import asyncio
import datetime
import time
from decimal import Decimal
from random import randrange

from web3 import Web3

from dexalot import Dexalot
from enums import OrderSide, OrderType, OrderStatus
from logger import get_logger

logger = get_logger('dexalot_market_maker')


class MarketMaker:

    def __init__(self, config):

        # MM Params
        self.dexalot = None
        self.config = config
        self.pair = config['trade_pair']
        self.target_spread = Decimal(config['target_spread'])
        self.order_price_tolerance = Decimal(config['order_price_tolerance'])
        self.order_amount_tolerance = Decimal(config['order_amount_tolerance'])
        self.additional_state_update = config['additional_state_update']
        self.n_price_levels = int(config['n_price_levels'])
        self.n_agg_orders = int(config['n_agg_orders'])

        # State Params
        self.open_orders = {}
        self.base_inventory = None
        self.quote_inventory = None
        self.bid_book = None
        self.ask_book = None
        self.best_bid_price = None
        self.best_bid_amount = None
        self.best_ask_price = None
        self.best_ask_amount = None
        self.mid_price = None
        self.updated_timestamp = None

    async def run(self, event_loop):

        # Initialize Dexalot Exchange Handler
        self.dexalot = Dexalot(base_url=self.config['base_url'], trade_pair=self.config['trade_pair'],
                               web3=self.config['web3'], trader_address=self.config['trader_address'],
                               timeout=self.config['timeout'])
        self.dexalot.initialize()
        log_line = '\n' + 50 * '-' + '\n'
        log_line += "Dexalot Market Initialized" + '\n'
        log_line += f"Trade Pair: {self.dexalot.trade_pair}" + '\n'
        log_line += f"Base Asset: Symbol - {self.dexalot.base_symbol} - EVM Decimals {self.dexalot.base_decimals} - Display Decimals {self.dexalot.base_display_decimals}" + '\n'
        log_line += f"Quote Asset: Symbol - {self.dexalot.quote_symbol} - EVM Decimals {self.dexalot.quote_decimals} - Display Decimals {self.dexalot.quote_display_decimals}" + '\n'
        log_line += f"Min Trade Amount: {self.dexalot.min_trade_amount}. Max Trade Amount: {self.dexalot.max_trade_amount}" + '\n'
        log_line += f"Target Spread: {self.target_spread}" + '\n'
        log_line += f"Order Price Tolerance: {self.order_price_tolerance}. Order Amount Tolerance: {self.order_amount_tolerance}" + '\n' + 50 * '-'
        logger.info(log_line)

        # Fetch Initial State
        self.update_state()
        if (self.best_bid_price == 0) and (self.best_ask_price == 0):
            self.mid_price = Decimal(self.config['default_mid_price'])
            logger.info(
                f"No orders in the book. Start quoting around default price value: {self.config['default_mid_price']} {self.dexalot.quote_symbol}")
        elif (self.best_bid_price == 0) or (self.best_ask_price == 0):
            self.mid_price = self.best_bid_price if not None else self.best_ask_price
            logger.info(
                f"Liquidity missing from one side of book. Start quoting around the available side: {self.mid_price} {self.dexalot.quote_symbol}")

        # Update out initial orders before starting
        self.update_orders()

        # Start event loops
        order_status_event_filter = self.dexalot.trade_pairs_contract.events.OrderStatusChanged.createFilter(
            fromBlock='latest')
        executed_event_filter = self.dexalot.trade_pairs_contract.events.Executed.createFilter(fromBlock='latest')

        event_loop.create_task(self.run_order_status_changed_listener(order_status_event_filter, 2))
        event_loop.create_task(self.run_executed_listener(executed_event_filter, 2))
        await self.run_additional_state_update()

    def update_orders(self, random=False):

        if random:
            self.mid_price = self.mid_price + Decimal(randrange(-10, 10) / 10)

        bid_price, ask_price = self.calculate_order_prices()
        bid_amount, ask_amount = self.calculate_order_amounts()

        buy_orders = [order for order in self.open_orders if order['side'] == OrderSide.BUY.value]
        if self.orders_require_action(buy_orders, bid_price, bid_amount):
            for order in buy_orders:
                logger.info(f"Cancelling BUY order: {order['id']}")
                self.dexalot.cancel_order(self.pair, order['id'])
            self.dexalot.add_order(self.pair, bid_price, bid_amount, OrderSide.BUY, OrderType.LIMIT)

        time.sleep(2)

        sell_orders = [order for order in self.open_orders if order['side'] == OrderSide.SELL.value]
        if self.orders_require_action(sell_orders, ask_price, ask_amount):
            for order in sell_orders:
                logger.info(f"Cancelling SELL order: {order['id']}")
                self.dexalot.cancel_order(self.pair, order['id'])
            self.dexalot.add_order(self.pair, ask_price, ask_amount, OrderSide.SELL, OrderType.LIMIT)

    def calculate_order_prices(self):
        bid_price = self.mid_price - (self.target_spread / 2)
        ask_price = self.mid_price + (self.target_spread / 2)

        return bid_price, ask_price

    def calculate_order_amounts(self):
        bid_amount = Decimal(self.config['default_amount'])
        ask_amount = Decimal(self.config['default_amount'])

        return bid_amount, ask_amount

    def within_tolerance(self, target_value: Decimal, order_value: Decimal, tolerance: Decimal) -> bool:
        tolerated = order_value * tolerance
        return bool((order_value < (target_value + tolerated)) and (order_value > (target_value - tolerated)))

    def orders_require_action(self, orders, price: Decimal, quantity: Decimal):

        # We only want one order open per side for now
        if len(orders) > 1:
            return True
        # Minimum spread check
        price_tolerance = self.order_price_tolerance
        amount_tolerance = self.order_amount_tolerance
        return len(orders) == 0 or not all(
            [(self.within_tolerance(price, Decimal(order['price']), self.order_price_tolerance)
              and self.within_tolerance(quantity, (Decimal(order['quantity']) - Decimal(order['quantityfilled'])),
                                        self.order_amount_tolerance))
             for order in orders])

    def update_state(self):

        self.open_orders = self.dexalot.fetch_open_orders()
        logger.info(f"Returned {len(self.open_orders)} Open Trades")
        bid_book, ask_book = self.dexalot.fetch_orderbook(self.n_price_levels, self.n_agg_orders)

        self.best_bid_price = Decimal(bid_book[0][0]) / 10 ** self.dexalot.quote_decimals
        self.best_bid_amount = Decimal(bid_book[1][0]) / 10 ** self.dexalot.base_decimals
        self.best_ask_price = Decimal(ask_book[0][0]) / 10 ** self.dexalot.quote_decimals
        self.best_ask_amount = Decimal(ask_book[1][0]) / 10 ** self.dexalot.base_decimals
        self.bid_book = bid_book
        self.ask_book = ask_book
        self.mid_price = self.calculate_mid(self.best_bid_price, self.best_ask_price)
        self.updated_timestamp = self.get_nanos()

        log_line = '\n' + 50 * '-' + '\n'
        log_line += "Updating State..." + '\n'
        log_line += f"Bid Book: {bid_book}" + '\n' + f"Ask Book: {ask_book}" + '\n'
        log_line += f"Best Bid - Price {self.best_bid_price} {self.dexalot.quote_symbol} - " \
                    f"Amount ({self.best_bid_amount} {self.dexalot.base_symbol})" + '\n'
        log_line += f"Best Ask - Price {self.best_ask_price} {self.dexalot.quote_symbol} - " \
                    f"Amount ({self.best_ask_amount} {self.dexalot.base_symbol})" + '\n'
        log_line += f"Mid Price {self.mid_price} {self.dexalot.quote_symbol}" + '\n' + 50 * '-'
        logger.info(log_line)

    async def run_additional_state_update(self):
        while True:
            # Update the market state and then our orders
            await asyncio.sleep(self.additional_state_update)
            try:
                self.update_state()
                self.update_orders()
            except Exception as e:
                logger.error(f"Could not update orders due to: {e}")

    def handle_order_status_changed(self, order_status_changed):

        pair = Web3.toText(order_status_changed.args.pair).split(str(b'\x00', 'utf8'))[0]
        id = order_status_changed.args.id.hex()
        order_status = OrderStatus(order_status_changed.args.status)
        order_side = OrderSide(order_status_changed.args.side)
        traderaddress = order_status_changed.args.traderaddress

        update_orders = False

        if pair == self.pair:
            # Perform sanity checks on our own orders
            if traderaddress == self.dexalot.trade_address:
                # Fetch the new world state and update our orders
                if order_status == OrderStatus.FILLED:
                    filled_quantity = Decimal(
                        order_status_changed.args.quantityfilled) / 10 ** self.dexalot.quote_decimals
                    logger.info(f"Order {id} FILLED {filled_quantity}/{filled_quantity} {self.dexalot.quote_symbol}")
                    update_orders = True

                elif order_status in [OrderStatus.REJECTED, OrderStatus.EXPIRED, OrderStatus.KILLED]:
                    logger.info(f"Order {id} ERROR... Updating state and replacing orders")
                    self.update_state()
                    self.update_orders()
                # Check remaining amount after partial fill and replenish order if over tolerance
                elif order_status == OrderStatus.PARTIAL:
                    filled_quantity = Decimal(
                        order_status_changed.args.quantityfilled) / 10 ** self.dexalot.base_decimals
                    total_quantity = Decimal(order_status_changed.args.quantity) / 10 ** self.dexalot.base_decimals
                    remaining_quantity = total_quantity - filled_quantity
                    logger.info(
                        f"Order {id} PARTIAL FILL {filled_quantity}/{total_quantity} {self.dexalot.base_symbol}")
                    bid_amount, ask_amount = self.calculate_order_amounts()

                    if order_side == OrderSide.BUY:
                        if not self.within_tolerance(bid_amount, remaining_quantity, self.order_amount_tolerance):
                            update_orders = True
                    elif order_side == OrderSide.SELL:
                        if not self.within_tolerance(ask_amount, remaining_quantity, self.order_amount_tolerance):
                            update_orders = True

            # Orders from others
            else:
                # If a new limit order then we check the new mid and adjust orders if needed
                if order_status == OrderStatus.NEW:
                    limit_price = Decimal(order_status_changed.args.price) / 10 ** self.dexalot.quote_decimals
                    limit_amount = Decimal(order_status_changed.args.quantity) / 10 ** self.dexalot.base_decimals
                    logger.info(f"NEW {repr(order_side)} LIMIT. Price {limit_price} {self.dexalot.quote_symbol} "
                                f"Amount {limit_amount} {self.dexalot.base_symbol} placed by {traderaddress}")
                    # If best bid increases or best ask decreases then we recalculate the mid and apdate orders
                    if (limit_price > self.best_bid_price) and (order_side == OrderSide.BUY):
                        logger.info(f"Best Bid moved from {self.best_bid_price} -> {limit_price}")
                        update_orders = True
                    elif (limit_price < self.best_ask_price) and (order_side == OrderSide.SELL):
                        logger.info(f"Best Ask moved from {self.best_ask_price} -> {limit_price}")
                        update_orders = True
                # If an existing limit order is removed or filled then we check to see if it was the best bid/ask and adjust orders if needed
                elif order_status in [OrderStatus.CANCELLED, OrderStatus.FILLED]:
                    limit_price = Decimal(order_status_changed.args.price) / 10 ** self.dexalot.quote_decimals
                    limit_amount = Decimal(order_status_changed.args.quantity) / 10 ** self.dexalot.base_decimals
                    logger.info(f"REMOVED {repr(order_side)} LIMIT. Price {limit_price} {self.dexalot.quote_symbol} "
                                f"Amount {limit_amount} {self.dexalot.base_symbol} placed by {traderaddress}")
                    if (limit_price == self.best_bid_price) or (limit_price == self.best_ask_price):
                        update_orders = True

            if update_orders:
                time.sleep(5)
                self.update_state()
                self.update_orders()

    def handler_executed(self, executed):
        """Current logic can all be handled via OrderStatusChanged events which are emitted alongside Executed events.
        Executed events could be used to determine useful features such as order aggressor that can be used to adjust skew/spread"""

        pair = Web3.toText(executed.args.pair).split(str(b'\x00', 'utf8'))[0]
        maker = executed.args.maker.hex()
        taker = executed.args.taker.hex()
        price = Decimal(executed.args.price) / 10 ** self.dexalot.quote_decimals
        amount = Decimal(executed.args.quantity) / 10 ** self.dexalot.base_decimals
        fee_maker = Decimal(executed.args.feeMaker) / 10 ** self.dexalot.quote_decimals
        fee_taker = Decimal(executed.args.feeTaker) / 10 ** self.dexalot.quote_decimals

        log_line = f"EXECUTED on {pair}. Price: {price} {self.dexalot.quote_symbol}. Amount: {amount} {self.dexalot.base_symbol}." + '\n'
        log_line += f"Maker: {maker} (fee paid: {fee_maker}). Taker: {taker} (fee_paid: {fee_taker})"
        logger.info(log_line)

    def cancel_all_transaction(self):
        order_id_list = []
        for order in self.open_orders:
            order_id_list.append(order['id'])
        self.dexalot.cancel_all_orders(self.pair, order_id_list)

    async def run_order_status_changed_listener(self, event_filter, poll_interval):
        while True:
            for order_status_changed in event_filter.get_new_entries():
                self.handle_order_status_changed(order_status_changed)
                await asyncio.sleep(poll_interval)

    async def run_executed_listener(self, event_filter, poll_interval):
        while True:
            for executed in event_filter.get_new_entries():
                self.handler_executed(executed)
                await asyncio.sleep(poll_interval)

    def calculate_mid(self, bid_price: Decimal, ask_price: Decimal) -> Decimal:
        if (bid_price == 0) and (ask_price == 0):
            return self.config['default_mid_price']
        elif (bid_price == 0) or (ask_price == 0):
            return bid_price + self.target_spread / 2 if ask_price == 0 else ask_price - self.target_spread / 2
        else:
            return (bid_price + ask_price) / 2

    def get_nanos(self) -> int:
        return int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 10 ** 9)

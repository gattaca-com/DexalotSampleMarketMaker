import datetime
from decimal import Decimal

from config import init_config
from dexalot import Dexalot
from enums import OrderSide, OrderType
from logger import get_logger

logger = get_logger('dexalot_market_maker')


class MarketMaker:

    def __init__(self, config):

        # MM Params
        self.config = config
        self.pair = config['trade_pair']
        self.spread = Decimal(config['spread'])
        self.existing_order_tolerance = Decimal(config['existing_order_tolerance'])
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

    def start(self):

        # Initialize Dexalot Exchange Handler
        self.dexalot = Dexalot(base_url=self.config['base_url'], trade_pair=self.config['trade_pair'],
                               web3=self.config['web3'], trader_address=config['trader_address'],
                               timeout=self.config['timeout'])
        self.dexalot.initialize()
        log_line = '\n' + 50*'-' + '\n'
        log_line += "Dexalot Market Initialized" + '\n'
        log_line += f"Trade Pair: {self.dexalot.trade_pair}" + '\n'
        log_line += f"Base Asset: Symbol - {self.dexalot.base_symbol} - EVM Decimals {self.dexalot.base_decimals} - Display Decimals {self.dexalot.base_display_decimals}" + '\n'
        log_line += f"Quote Asset: Symbol - {self.dexalot.quote_symbol} - EVM Decimals {self.dexalot.quote_decimals} - Display Decimals {self.dexalot.quote_display_decimals}" + '\n'
        log_line += f"Min Trade Amount: {self.dexalot.min_trade_amount}. Max Trade Amount: {self.dexalot.max_trade_amount}" + '\n' + 50*'-'
        logger.info(log_line)

        # Fetch Initial State
        self.update_state()
        if (self.best_bid_price == 0) and (self.best_ask_price == 0):
            self.mid_price = Decimal(self.config['default_mid_price'])
            logger.info(f"No orders in the book. Start quoting around default price value: {self.config['default_mid_price']} {self.dexalot.quote_symbol}")
        elif (self.best_bid_price == 0) or (self.best_ask_price == 0):
            self.mid_price = self.best_bid_price if not None else self.best_ask_price
            logger.info(f"Liquidity missing from one side of book. Start quoting around the available side: {self.mid_price} {self.dexalot.quote_symbol}")

        self.open_orders = self.dexalot.fetch_open_orders()
        if len(self.open_orders) == 0:
            logger.info(f"No open orders")

        for order in self.open_orders:
            print(order)

        self.update_orders()

    def update_orders(self):

        bid_price, ask_price = self.calculate_order_prices()
        bid_amount, ask_amount = self.calculate_order_amounts()

        buy_orders = [order for order in self.open_orders if order['side'] == OrderSide.BUY.value]
        if self.orders_require_action(buy_orders, bid_price, bid_amount):
            logger.info("Cancelling BUY orders")
            for order in buy_orders:
                self.dexalot.cancel_order(self.pair, order['id'])
            self.dexalot.add_order(self.pair, bid_price, bid_amount, OrderSide.BUY, OrderType.LIMIT)

        sell_orders = [order for order in self.open_orders if order['side'] == OrderSide.SELL.value]
        if self.orders_require_action(sell_orders, ask_price, ask_amount):
            logger.info("Cancelling SELL orders")
            for order in sell_orders:
                self.dexalot.cancel_order(self.pair, order['id'])
            self.dexalot.add_order(self.pair, ask_price, ask_amount, OrderSide.SELL, OrderType.LIMIT)

    def calculate_order_prices(self):
        bid_price = self.mid_price - (self.spread / 2)
        ask_price = self.mid_price + (self.spread / 2)

        return bid_price, ask_price

    def calculate_order_amounts(self):
        bid_amount = Decimal(self.config['default_amount'])
        ask_amount = Decimal(self.config['default_amount'])

        return bid_amount, ask_amount

    def orders_require_action(self, orders, price: Decimal, quantity: Decimal):

        def within_tolerance(target_value: Decimal, order_value: Decimal) -> bool:
            tolerated = order_value * self.existing_order_tolerance
            return bool((order_value < (target_value + tolerated)) and (order_value > (target_value - tolerated)))

        return len(orders) == 0 or not all(
            [(within_tolerance(price, Decimal(order['price'])) and within_tolerance(quantity, Decimal(order['quantity']))) for order in orders])

    # def event_listener(self):
    #     trade_pairs_contract = self.dexalot_exchange.trade_pairs_contract
    #     event_filter = trade_pairs_contract.events.OrderStatusChanged.createFilter(fromBlock='latest')
    #     loop = asyncio.get_event_loop()

    def update_state(self):
        bid_book, ask_book = self.dexalot.fetch_orderbook(self.n_price_levels, self.n_agg_orders)

        self.best_bid_price = Decimal(bid_book[0][0]) / 10 ** self.dexalot.quote_decimals
        self.best_bid_amount = Decimal(bid_book[1][0]) / 10 ** self.dexalot.base_decimals
        self.best_ask_price = Decimal(ask_book[0][0]) / 10 ** self.dexalot.quote_decimals
        self.best_ask_amount = Decimal(ask_book[1][0]) / 10 ** self.dexalot.base_decimals
        self.bid_book = bid_book
        self.ask_book = ask_book
        self.mid_price = self.calculate_mid(self.best_bid_price, self.best_ask_price)
        self.updated_timestamp = self.get_nanos()

        log_line = '\n' + 50*'-' + '\n'
        log_line += "Updating State..." + '\n'
        log_line += f"Bid Book: {bid_book}" + '\n' + f"Ask Book: {ask_book}" + '\n'
        log_line += f"Best Bid - Price {self.best_bid_price} {self.dexalot.quote_symbol} - " \
                    f"Amount ({self.best_bid_amount} {self.dexalot.base_symbol})" + '\n'
        log_line += f"Best Ask - Price {self.best_ask_price} {self.dexalot.quote_symbol} - " \
                    f"Amount ({self.best_ask_amount} {self.dexalot.base_symbol})" + '\n'
        log_line += f"Mid Price {self.mid_price} {self.dexalot.quote_symbol}" + '\n' + 50*'-'
        logger.info(log_line)

    def calculate_mid(self, bid_price: Decimal, ask_price: Decimal) -> Decimal:
        return (bid_price + ask_price) / 2

    def get_nanos(self) -> int:
        return int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 10 ** 9)


if __name__ == '__main__':
    config = init_config()
    market_maker = MarketMaker(config)
    market_maker.start()

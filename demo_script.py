import asyncio
import datetime
import time
from decimal import Decimal
from web3 import Web3

from config import init_config
from dexalot import Dexalot
from enums import OrderSide, OrderType, OrderStatus
from logger import get_logger
from market_maker import MarketMaker

logger = get_logger('dexalot-demo')


def run_demo(config):
    # Initialize Dexalot Exchange Handler and GET reference data
    dexalot = Dexalot(base_url=config['base_url'], trade_pair=config['trade_pair'], web3=config['web3'],
                      trader_address=config['trader_address'], timeout=config['timeout'])

    target_spread = config['target_spread']
    order_price_tolerance = config['order_price_tolerance']
    order_amount_tolerance = config['order_amount_tolerance']

    dexalot.initialize()
    log_line = '\n' + 50 * '-' + '\n'
    log_line += "Dexalot Market Initialized" + '\n'
    log_line += f"Trade Pair: {dexalot.trade_pair}" + '\n'
    log_line += f"Base Asset: Symbol - {dexalot.base_symbol} - EVM Decimals {dexalot.base_decimals} - Display Decimals {dexalot.base_display_decimals}" + '\n'
    log_line += f"Quote Asset: Symbol - {dexalot.quote_symbol} - EVM Decimals {dexalot.quote_decimals} - Display Decimals {dexalot.quote_display_decimals}" + '\n'
    log_line += f"Min Trade Amount: {dexalot.min_trade_amount}. Max Trade Amount: {dexalot.max_trade_amount}" + '\n'
    log_line += f"Target Spread: {target_spread}" + '\n'
    log_line += f"Order Price Tolerance: {order_price_tolerance}. Order Amount Tolerance: {order_amount_tolerance}" + '\n' + 50 * '-'
    logger.info(log_line)

    # Deposit some funds
    # dexalot.deposit_token(1, is_base=True)
    # dexalot.deposit_token(1, is_base=False)

    # Create MM Instance
    market_maker = MarketMaker(config)
    market_maker.dexalot = dexalot

    # Fetch Initial State (Orderbook + Open Orders) and place orders if not already present
    market_maker.update_state()
    if (market_maker.best_bid_price == 0) and (market_maker.best_ask_price == 0):
        market_maker.mid_price = Decimal(config['default_mid_price'])
        logger.info(f"No orders in the book. Start quoting around default price value: {config['default_mid_price']} {dexalot.quote_symbol}")
    elif (market_maker.best_bid_price == 0) or (market_maker.best_ask_price == 0):
        market_maker.mid_price = market_maker.best_bid_price if not None else market_maker.best_ask_price
        logger.info(f"Liquidity missing from one side of book. Start quoting around the available side: {market_maker.mid_price} {dexalot.quote_symbol}")

    market_maker.update_orders()

    # Wait 10 seconds and cancel orders individually
    time.sleep(10)
    market_maker.update_state()
    open_orders = market_maker.open_orders
    for order in open_orders:
        dexalot.cancel_order(dexalot.trade_pair, order['id'])

    # Wait 20 seconds and place new (different) buy and sell orders
    time.sleep(20)
    market_maker.update_state()
    market_maker.update_orders(random=True)

    # Wait 30 seconds and cancel all positions
    time.sleep(30)
    market_maker.update_state()
    market_maker.cancel_all_transaction()


if __name__ == '__main__':
    config = init_config()
    run_demo(config)
import asyncio
import requests
import web3.eth
import json
from enums import OrderSide, OrderType, OrderStatus
from config import init_config
from web3 import Web3
from logger import get_logger
from decimal import Decimal

logger = get_logger("Dexalot")


class Dexalot:

    # Base URL
    # https://api.dexalot-dev.com/api/

    def __init__(self, base_url: str, pair: str, web3: Web3, timeout=None):

        self.base_url = base_url
        self.pair = pair
        self.base_symbol = None
        self.quote_symbol = None
        self.base_display_decimals = None
        self.quote_display_decimals = None
        self.base_address = None
        self.quote_address = None
        self.min_trade_amount = None
        self.max_trade_amount = None
        self.base_decimals = None
        self.quote_decimals = None
        self.web3 = web3
        self.exchange_contract = None
        self.portfolio_contract = None
        self.trade_pairs_contract = None
        self.orderbooks_contract = None
        self.timeout = timeout

    def initialize(self):

        # Fetch Trading Pair MetaData
        pair_data = self.fetch_single_pair(self.pair)
        self.base_symbol = str(pair_data['base'])
        self.quote_symbol = str(pair_data['quote'])
        self.base_display_decimals = int(pair_data['basedisplaydecimals'])
        self.quote_display_decimals = int(pair_data['quotedisplaydecimals'])
        self.base_address = self.web3.toChecksumAddress(pair_data['baseaddress'])
        self.quote_address = self.web3.toChecksumAddress(pair_data['quoteaddress']) if pair_data['quoteaddress'] else None
        self.min_trade_amount = float(pair_data['mintrade_amnt'])
        self.max_trade_amount = float(pair_data['maxtrade_amnt'])
        self.base_decimals = int(pair_data['base_evmdecimals'])
        self.quote_decimals = int(pair_data['quote_evmdecimals'])
        logger.info(f"Retrieved pair reference data for {self.pair}: {pair_data}")
        #
        # # Initialize Exchange Contract
        # contract_info = self.fetch_contract_and_abi(deployment_type="Exchange")
        # self.exchange_contract = self.web3.eth.contract(address=contract_info["address"], abi=contract_info["abi"]["abi"])
        #
        # # Initialize Portfolio Contract
        # contract_info = self.fetch_contract_and_abi(deployment_type="Portfolio")
        # self.portfolio_contract = self.web3.eth.contract(address=contract_info["address"], abi=contract_info["abi"]["abi"])

        # Initialize TradePairs Contract
        contract_info = self.fetch_contract_and_abi(deployment_type="TradePairs")
        self.trade_pairs_contract = self.web3.eth.contract(address=contract_info["address"], abi=contract_info["abi"]["abi"])

        # # Initialize Orderbook Contract
        # contract_info = self.fetch_contract_and_abi(deployment_type="OrderBooks")
        # self.orderbooks_contract = self.web3.eth.contract(address=contract_info["address"], abi=contract_info["abi"]["abi"])
        # logger.info("All contracts have been initialized and ready to trade")

    async def event_loop(self, event_filter, poll_interval):
        while True:
            for OrderStatusChanged in event_filter.get_new_entries():
                print(OrderStatusChanged)
                print(Web3.toJSON(OrderStatusChanged))
                await asyncio.sleep(poll_interval)

    def event_listener(self):

        event_filter = self.trade_pairs_contract.events.OrderStatusChanged.createFilter(fromBlock='latest')
        loop = asyncio.get_event_loop()

        try:
            loop.run_until_complete(asyncio.gather(self.event_loop(event_filter, 2)))
        finally:
            loop.close()

    def fetch_tokens(self) -> list:

        # https://api.dexalot-dev.com/api/trading/pairs
        path = "trading/tokens"
        all_tokens = self._curl_dexalot(path=path)
        deployed_tokens = []

        for token in all_tokens:
            if token['status'] == 'deployed':
                deployed_tokens.append(token)

        return deployed_tokens

    def fetch_all_pairs(self) -> list:

        # https://api.dexalot-dev.com/api/trading/pairs
        path = "trading/pairs"
        all_pairs = self._curl_dexalot(path=path)
        deployed_pairs = []

        for pair in all_pairs:
            if pair['status'] == 'deployed':
                deployed_pairs.append(pair)
        return deployed_pairs

    def fetch_single_pair(self, single_pair: str):

        deployed_pairs = self.fetch_all_pairs()
        for pair_data in deployed_pairs:
            if pair_data['pair'] == single_pair:
                return pair_data
        logger.warning(f"Could not find {single_pair} in deployed pairs")
        return None

    def fetch_contract_and_abi(self, deployment_type: str):

        # https://api.dexalot-dev.com/api/trading/deploymentabi
        response = None
        if deployment_type in ["Exchange", "Portfolio", "TradePairs", "OrderBooks"]:
            path = "trading/deploymentabi/" + deployment_type
            response = self._curl_dexalot(path)
        else:
            logger.info("deployment_type must be either Exchange, Portfolio, TradePairs or OrderBooks")

        return response

    def place_order(self, trade_pair_id, price: Decimal, quantity: Decimal, side: OrderSide, type: OrderType):

        if (quantity < self.min_trade_amount) or (quantity > self.max_trade_amount):
            logger.info(f"Order size {quantity:.3f} must be between {self.min_trade_amount} and {self.max_trade_amount}")
            return None

        price_norm = int(round(price, self.quote_display_decimals)*10**self.quote_decimals)
        quantity_norm = int(round(quantity, self.base_display_decimals)*10**self.base_decimals)
        order_txn = self.trade_pairs_contract.functions.addOrder(trade_pair_id, price_norm, quantity_norm, side, type).transact()
        order_receipt = web3.eth.getTransactionReceipt(order_txn)
        print(order_receipt)
        return order_receipt

    def fetch_open_orders(self, trader_address: str):

        trader_address = web3.utils.toChecksumAddress(trader_address)
        # https://api.dexalot.com/api/trading/openorders/params?traderaddress=0xeB45E8926896CEd4e1de1b5617A6cA32DeDC15d2&itemsperpage=50&pageno=1
        open_orders = None
        return open_orders

    def fetch_orders(self, trader_address: str):

        trader_address = web3.utils.toChecksumAddress(trader_address)
        # https://api.dexalot.com/api/trading/orders/params?traderaddress=0xeB45E8926896CEd4e1de1b5617A6cA32DeDC15d2&itemsperpage=50&pageno=1
        orders = None
        return orders

    def fetch_orderbook(self):
        pass

    def _curl_dexalot(self, path, query=None, params=None, timeout=None, max_retries=None):

        url = self.base_url + path

        if timeout is None:
            timeout = self.timeout

        def retry():
            self.retries += 1
            if self.retries > max_retries:
                raise Exception("Max retries on %s (%s) hit, raising." % (path, json.dumps(params or '')))
            return self._curl_dexalot(path, query, params, timeout, max_retries)

        response = None
        try:
            response = requests.get(url, params=params)
        except requests.exceptions.Timeout as e:
            logger.warning("Timed out on request: %s (%s), retrying..." % (path, json.dumps(params or '')))
            return retry()

        return json.loads(response.text)


if __name__ == "__main__":

    config = init_config()

    pair = config['trade_pair']
    web3 = config['web3']

    base_url = "https://api.dexalot-dev.com/api/"
    exchange_handler = Dexalot(base_url, pair=pair, web3=web3, timeout=None)

    exchange_handler.initialize()

    # tokens = exchange_handler.fetch_tokens()
    # print(tokens)
    # pairs = exchange_handler.fetch_all_pairs()
    # print(pairs)
    price = Decimal(419.0000)
    amount = Decimal(0.35)

    # displaydecimals
    # ': 1, '
    # quotedisplaydecimals
    # ': 4
    #

    #order = exchange_handler.place_order(b"TEAM2/AVAX", price, amount, OrderSide.BUY, OrderType.LIMIT)

    exchange_handler.event_listener()

    # exchange_contract = exchange_handler.fetch_contract_and_abi("Exchange")
    # print(exchange_contract)
    # portfolio_contract = exchange_handler.fetch_contract_and_abi("Portfolio")
    # print(portfolio_contract)
    # trade_pairs_contract = exchange_handler.fetch_contract_and_abi("TradePairs")
    # print(trade_pairs_contract)
    # orderbooks_contract = exchange_handler.fetch_contract_and_abi("OrderBooks")
    # print(orderbooks_contract)
    #
    # orderbooks_contract = exchange_handler.fetch_contract_and_abi("tes")
    # print(orderbooks_contract)


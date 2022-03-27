import asyncio
import requests
import web3.eth
import json
from enums import OrderSide, OrderType, OrderStatus
from config import init_config, extract_environment_variable
from web3 import Web3
from logger import get_logger
from decimal import Decimal

logger = get_logger("dexalot_exchange")


class Dexalot:

    # Base URL
    # https://api.dexalot-dev.com/api/

    def __init__(self, base_url: str, trade_pair: str, web3: Web3, trader_address, timeout=None):

        self.base_url = base_url
        self.trade_pair = trade_pair
        self.web3 = web3
        self.trade_address = trader_address
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
        self.exchange_contract = None
        self.portfolio_contract = None
        self.trade_pairs_contract = None
        self.orderbooks_contract = None
        self.timeout = timeout

    def initialize(self):

        # Fetch Trading Pair MetaData
        pair_data = self.fetch_single_pair(self.trade_pair)
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
        logger.info(f"Retrieved pair reference data for {self.trade_pair}: {pair_data}")

        # # Initialize Exchange Contract
        # contract_info = self.fetch_contract_and_abi(deployment_type="Exchange")
        # self.exchange_contract = self.web3.eth.contract(address=contract_info["address"], abi=contract_info["abi"]["abi"])

        # Initialize Portfolio Contract
        contract_info = self.fetch_contract_and_abi(deployment_type="Portfolio")
        self.portfolio_contract = self.web3.eth.contract(address=contract_info["address"], abi=contract_info["abi"]["abi"])

        # Initialize TradePairs Contract
        contract_info = self.fetch_contract_and_abi(deployment_type="TradePairs")
        self.trade_pairs_contract = self.web3.eth.contract(address=contract_info["address"], abi=contract_info["abi"]["abi"])

        # Initialize Orderbook Contract
        contract_info = self.fetch_contract_and_abi(deployment_type="OrderBooks")
        self.orderbooks_contract = self.web3.eth.contract(address=contract_info["address"], abi=contract_info["abi"]["abi"])
        logger.info("All contracts have been initialized and ready to trade")

    def deposit_token(self, quantity: Decimal, is_base=True):

        deposit_token = self.base_symbol if is_base else self.quote_symbol
        logger.info(f"Depositing {quantity} {deposit_token}")
        trade_pair = bytes(self.trade_pair, 'utf8')
        trader_address = Web3.toChecksumAddress(self.trade_address)
        quantity = int(quantity * 10 ** self.quote_decimals)
        deposit_token = self.trade_pairs_contract.functions.getSymbol(trade_pair, is_base).call()

        if is_base:
            txn = self.portfolio_contract.functions.depositToken(trader_address, deposit_token, quantity).transact()
            txn_receipt = self.web3.eth.wait_for_transaction_receipt(txn)
        else:
            # Send directly to the contract as AVAX fails check in tokenList.contains(_symbol)
            # https://github.com/Dexalot/contracts/blob/8d4aa94e6b05ac2a4df7ede6f03c94e1bf3b5831/contracts/Portfolio.sol#L272
            txn = {
                'to': self.portfolio_contract.address,
                'value': quantity,
                'chainId': self.web3.eth.chainId,
                'nonce': self.web3.eth.get_transaction_count(self.web3.eth.default_account),
                'gas': 200000,
                'gasPrice': web3.toWei('100', 'gwei'),
            }
            signed_txn = self.web3.eth.account.sign_transaction(txn, private_key=extract_environment_variable('PRIVATE_KEY'))
            txn = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
            txn_receipt = self.web3.eth.wait_for_transaction_receipt(txn)

        return txn_receipt

    def fetch_tokens(self) -> list:

        # https://api.dexalot-dev.com/api/trading/pairs
        path = "trading/tokens"
        all_tokens = self._request_dexalot(path=path)
        deployed_tokens = []

        for token in all_tokens:
            if token['status'] == 'deployed':
                deployed_tokens.append(token)

        return deployed_tokens

    def fetch_all_pairs(self) -> list:

        # https://api.dexalot-dev.com/api/trading/pairs
        path = "trading/pairs"
        all_pairs = self._request_dexalot(path=path)
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
            response = self._request_dexalot(path)
        else:
            logger.info("deployment_type must be either Exchange, Portfolio, TradePairs or OrderBooks")

        return response

    def fetch_open_orders(self) -> list:

        # https://api.dexalot-dev.com/api/trading/openorders
        path = "trading/openorders/params"
        params = {'traderaddress': self.trade_address, 'pair': self.trade_pair}
        response = self._request_dexalot(path=path, params=params)
        return response['rows']

    def fetch_order_status(self, order_id):

        order_id_bytes = bytes.fromhex(order_id[2:])
        order_info = self.trade_pairs_contract.functions.getOrder(order_id_bytes).call()
        return order_info

    def fetch_orderbook(self, price_levels: int, aggregated_orders: int):
        """
        _orderBookID: e.g AVAX/ALOT-BUYBOOK.
        nPrice: depth requested. if 1 top of the book is returned.
        nOrder: number of orders to be retrieved at the price point.
        lastPrice: the price point to start in case a loop is used to get the entire order book. Use 0 for small requests.
        lastOrder: the orderid used in case a loop is used to get the entire order book. Use empty string in bytes32 for small requests.
        _type: get lowest (_type=0) or highest (_type=1) n orders as tuples of price, quantity. Use 1 for bid to get highest values
        """
        bid_book_id = bytes(self.trade_pair + '-BUYBOOK', 'utf-8')
        ask_book_id = bytes(self.trade_pair + '-SELLBOOK', 'utf-8')
        bid_book = self.orderbooks_contract.functions.getNOrders(bid_book_id, price_levels, aggregated_orders, 0, b'', 1).call()
        ask_book = self.orderbooks_contract.functions.getNOrders(ask_book_id, price_levels, aggregated_orders, 0, b'', 0).call()
        return bid_book[:2], ask_book[:2]

    def add_order(self, trade_pair_id, price: Decimal, base_amount: Decimal, order_side: OrderSide, order_type: OrderType):

        quote_amount = base_amount * price
        if (quote_amount < self.min_trade_amount) or (quote_amount > self.max_trade_amount):
            logger.info(f"Order size {quote_amount:.3f} {self.quote_symbol} must be between {self.min_trade_amount} and {self.max_trade_amount}")
            return None

        price_norm = int(round(price, self.quote_display_decimals)*10**self.quote_decimals)
        base_amount_norm = int(round(base_amount, self.base_display_decimals)*10**self.base_decimals)
        trade_pair_id_bytes = bytes(trade_pair_id, 'utf-8')
        order_txn = self.trade_pairs_contract.functions.addOrder(trade_pair_id_bytes, price_norm, base_amount_norm, order_side.value, order_type.value).transact()
        logger.info(f"Placed {repr(order_type)} {repr(order_side)} Order. Price {price:.4f}. Size {base_amount:.4f} {self.base_symbol}")
        return order_txn

    def cancel_order(self, trade_pair_id: str, order_id: str):
        # Strip 0x from order_id string and convert to bytes
        order_id_bytes = bytes.fromhex(order_id[2:])
        trade_pair_id_bytes = bytes(trade_pair_id, 'utf-8')
        self.trade_pairs_contract.functions.cancelOrder(trade_pair_id_bytes, order_id_bytes).transact()
        logger.info(f"Cancelled {order_id}")

    def cancel_all_orders(self, trade_pair_id: str, order_id_list: list):
        # Strip 0x from order_ids and convert to bytes
        # TODO: Add logic to cancel in batches if more than 20 orders
        trade_pair_id = bytes(trade_pair_id, 'utf-8')
        order_id_bytes_list = []
        for order_id in order_id_list:
            order_id_bytes = bytes.fromhex(order_id[2:])
            order_id_bytes_list.append(order_id_bytes)

        self.trade_pairs_contract.functions.cancelAllOrders(trade_pair_id, order_id_bytes_list).transact()
        logger.info(f"Cancelled All Orders")

    def _request_dexalot(self, path, query=None, params=None, timeout=None, max_retries=None):

        url = self.base_url + path

        if timeout is None:
            timeout = self.timeout

        def retry():
            self.retries += 1
            if self.retries > max_retries:
                raise Exception("Max retries on %s (%s) hit, raising." % (path, json.dumps(params or '')))
            return self._request_dexalot(path, query, params, timeout, max_retries)

        try:
            response = requests.get(url=url, params=params)
        except requests.exceptions.Timeout as e:
            logger.warning("Timed out on request: %s (%s), retrying..." % (path, json.dumps(params or '')))
            return retry()

        return json.loads(response.text)


if __name__ == "__main__":

    config = init_config()

    pair = config['trade_pair']
    web3 = config['web3']
    trader_address = config['trader_address']

    base_url = "https://api.dexalot-dev.com/api/"
    exchange_handler = Dexalot(base_url, trade_pair=pair, web3=web3, trader_address=trader_address, timeout=None)

    exchange_handler.initialize()

    receipt = exchange_handler.deposit_token(quantity=Decimal(1), is_base=False)
    print(receipt)
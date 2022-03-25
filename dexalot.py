import requests
import web3.eth
import json
from config import init_config
from web3 import Web3
from logger import get_logger

logger = get_logger("Dexalot")


class Dexalot:

    # Base URL
    # https://api.dexalot-dev.com/api/

    def __init__(self, base_url: str, pair: str, web3: Web3, timeout=None):

        self.base_url = base_url
        self.symbol = pair
        self.web3 = web3
        self.exchange_contract = None
        self.portfolio_contract = None
        self.trade_pairs_contract = None
        self.orderbooks_contract = None
        self.timeout = timeout

    def initialize_contracts(self):

        contract_info = self.fetch_contract_and_abi(deployment_type="Exchange")
        self.exchange_contract = self.web3.eth.contract(address=contract_info["address"], abi=contract_info["abi"]["abi"])

        contract_info = self.fetch_contract_and_abi(deployment_type="Portfolio")

        self.portfolio_contract = self.web3.eth.contract(address=contract_info["address"], abi=contract_info["abi"]["abi"])

        contract_info = self.fetch_contract_and_abi(deployment_type="TradePairs")
        self.trade_pairs_contract = self.web3.eth.contract(address=contract_info["address"], abi=contract_info["abi"]["abi"])

        contract_info = self.fetch_contract_and_abi(deployment_type="OrderBooks")
        self.orderbooks_contract = self.web3.eth.contract(address=contract_info["address"], abi=contract_info["abi"]["abi"])
        logger.info("All contracts have been initialized and ready to trade")

    def fetch_tokens(self) -> list:

        # https://api.dexalot-dev.com/api/trading/pairs
        path = "trading/tokens"
        all_tokens = self._curl_dexalot(path=path)
        deployed_tokens = []

        for token in all_tokens:
            if token['status'] == 'deployed':
                deployed_tokens.append(token)

        return deployed_tokens

    def fetch_pairs(self) -> list:

        # https://api.dexalot-dev.com/api/trading/pairs
        path = "trading/pairs"
        all_pairs = self._curl_dexalot(path=path)
        deployed_pairs = []

        for pair in all_pairs:
            if pair['status'] == 'deployed':
                deployed_pairs.append(pair)
        return deployed_pairs

    def fetch_contract_and_abi(self, deployment_type: str):

        # https://api.dexalot-dev.com/api/trading/deploymentabi
        response = None
        if deployment_type in ["Exchange", "Portfolio", "TradePairs", "OrderBooks"]:
            path = "trading/deploymentabi/" + deployment_type
            response = self._curl_dexalot(path)
        else:
            logger.info("deployment_type must be either Exchange, Portfolio, TradePairs or OrderBooks")

        return response

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

    from web3 import HTTPProvider, Web3
    from web3.middleware import geth_poa_middleware

    pair = "TEAM2/WAVAX"

    url_devnet = "https://node.dexalot-dev.com/ext/bc/C/rpc"
    my_web3 = Web3(HTTPProvider(url_devnet))
    my_web3.middleware_onion.inject(geth_poa_middleware, layer=0)

    base_url = "https://api.dexalot-dev.com/api/"
    exchange_handler = Dexalot(base_url, pair=pair, web3=my_web3, timeout=None)

    exchange_handler.initialize_contracts()
    exchange_handler.orderbooks_contract.functions.
    # tokens = exchange_handler.fetch_tokens()
    # print(tokens)
    #
    # pairs = exchange_handler.fetch_pairs()
    # print(pairs)
    #
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


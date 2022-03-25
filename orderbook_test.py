from web3 import HTTPProvider, Web3
from web3.middleware import geth_poa_middleware
import json

url_mainnet = "http://54.217.117.72:9650/ext/bc/C/rpc"
web3 = Web3(HTTPProvider(url_mainnet))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)

with open("abis/orderbook.json") as file:
    orderbook_abi = json.load(file)

contract_address = web3.toChecksumAddress("0x3Ece76F7AdD934Fb8a35c9C371C4D545e299669A")
orderbook_contract = web3.eth.contract(address=contract_address, abi=orderbook_abi)
orderbook_contract.functions.getBookSize("AVAX/USDT-BUYBOOK").call()
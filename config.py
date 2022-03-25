from web3 import HTTPProvider, Web3
from web3.middleware import geth_poa_middleware


def init_config():
    config = {}

    url_mainnet = "http://54.217.117.72:9650/ext/bc/C/rpc"
    my_web3 = Web3(HTTPProvider(url_mainnet))
    my_web3.middleware_onion.inject(geth_poa_middleware, layer=0)
    config["web3"] = my_web3

    config["trade_pair"] = "TEAM1/AVAX"

    # MM Config
    config["spread"] = 10.0

    return config

from web3 import HTTPProvider, Web3
from web3.middleware import geth_poa_middleware
import os

from web3_utils import register_private_key


class ExpectedEnvironmentPropertyException(Exception):
    def __init__(self, environment_val):
        self.message = "Expected to find %s in environment but was not found" % environment_val
        super().__init__(self.message)


def extract_environment_variable(var):
    env_var = os.environ.get(var, None)
    if not env_var:
        raise ExpectedEnvironmentPropertyException(var)
    return env_var


def init_config():
    config = {}

    ulr_devnet = 'https://node.dexalot-dev.com/ext/bc/C/rpc'
    web3 = Web3(HTTPProvider(ulr_devnet))
    web3.middleware_onion.inject(geth_poa_middleware, layer=0)

    private_key = extract_environment_variable('PRIVATE_KEY')
    register_private_key(web3, private_key)

    # Web3 Config
    config['trader_address'] = web3.eth.default_account
    config['web3'] = web3

    # Exchange Handler Config
    config['base_url'] = 'https://api.dexalot-dev.com/api/'
    config['timeout'] = 10
    config['trade_pair'] = 'TEAM2/AVAX'

    # MM Config
    config['default_mid_price'] = 20            # Default mid price if no market
    config['existing_order_tolerance'] = 0.1    # Tolerance when comparing orders (10% = 0.1)
    config['default_amount'] = 5.1
    config['spread'] = 1
    config['n_price_levels'] = 5
    config['n_agg_orders'] = 50

    return config

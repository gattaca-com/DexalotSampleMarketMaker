from eth_account.signers.local import LocalAccount
from web3.middleware import construct_sign_and_send_raw_middleware
from web3 import Web3
from eth_account import Account
from web3.types import SignedTx

_registered_accounts = {}


def register_private_key(web3: Web3, private_key):
    assert (isinstance(web3, Web3))
    account = Account.privateKeyToAccount(private_key)

    _registered_accounts[(web3, account.address)] = account
    web3.middleware_onion.add(construct_sign_and_send_raw_middleware(account))
    web3.eth.default_account = account.address


def sign_tx(tx, web3: Web3) -> SignedTx:
    account: LocalAccount = _registered_accounts[(web3, web3.eth.defaultAccount)]
    return account.sign_transaction(tx)

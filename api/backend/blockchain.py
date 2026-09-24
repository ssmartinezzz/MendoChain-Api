import logging

from algosdk import constants
from algosdk import transaction
from algosdk.v2client import algod

logger = logging.getLogger(__name__)


class BlockchainError(Exception):
    """The transaction could not be submitted to the network."""


def first_transaction_example(private_key, my_address, message):
    """Submit a zero-amount payment carrying `message` and return its transaction id.

    Raises BlockchainError when the transaction is not submitted. Once submitted, the id is
    returned even if confirmation times out, because the transaction is already on its way on chain.
    """
    algo_token_local = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    algo_address_local = "http://localhost:4001"
    algod_address = "https://testnet-api.algonode.cloud"
    algod_token = ""
    algod_client = algod.AlgodClient(algod_token, algod_address)

    try:
        account_info = algod_client.account_info(my_address)
        logger.info("Account balance: %s microAlgos", account_info.get('amount'))

        # build transaction
        params = algod_client.suggested_params()
        params.flat_fee = constants.MIN_TXN_FEE
        params.fee = 1000
        receiver = "HZ57J3K46JIJXILONBBZOHX6BKPXEM2VVXNRFSUED6DKFD5ZD24PMJ3MVA"
        amount = 0
        note = message.encode()

        unsigned_txn = transaction.PaymentTxn(my_address, params, receiver, amount, None, note)
        signed_txn = unsigned_txn.sign(private_key)
        txid = algod_client.send_transaction(signed_txn)
    except Exception as err:
        raise BlockchainError(str(err)) from err

    try:
        transaction.wait_for_confirmation(algod_client, txid, 4)
    except Exception:
        logger.warning("Transaction %s submitted but not confirmed yet", txid, exc_info=True)
    return txid

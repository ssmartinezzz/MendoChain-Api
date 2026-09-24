import logging

from algosdk import constants, transaction
from algosdk.v2client import algod
from django.conf import settings

from api.traceability.domain.errors import LedgerUnavailable

logger = logging.getLogger(__name__)


class AlgorandLedger:
    """LedgerGateway that records each note as a zero-amount Algorand payment."""

    def __init__(self, client, sender, private_key, receiver, confirmation_rounds=4):
        self.client = client
        self.sender = sender
        self.private_key = private_key
        self.receiver = receiver
        self.confirmation_rounds = confirmation_rounds

    def record(self, note):
        try:
            params = self.client.suggested_params()
            params.flat_fee = True
            params.fee = constants.MIN_TXN_FEE
            unsigned = transaction.PaymentTxn(self.sender, params, self.receiver, 0, note=note.encode())
            tx_id = self.client.send_transaction(unsigned.sign(self.private_key))
        except Exception as err:
            raise LedgerUnavailable(str(err)) from err

        # Once submitted the transaction is on its way on chain, so its id is kept even if confirmation times out.
        try:
            transaction.wait_for_confirmation(self.client, tx_id, self.confirmation_rounds)
        except Exception:
            logger.warning('Transaction %s submitted but not confirmed yet', tx_id, exc_info=True)
        return tx_id


def build_algorand_ledger():
    return AlgorandLedger(
        client=algod.AlgodClient(settings.ALGOD_TOKEN, settings.ALGOD_ADDRESS),
        sender=settings.ALGORAND_SENDER,
        private_key=settings.ALGORAND_PRIVATE_KEY,
        receiver=settings.ALGORAND_RECEIVER,
    )

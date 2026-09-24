import base64
from unittest import mock

from algosdk import account
from algosdk.error import AlgodHTTPError
from algosdk.transaction import SuggestedParams
from django.test import SimpleTestCase, override_settings

from api.traceability.domain.errors import LedgerUnavailable
from api.traceability.infrastructure.algorand import AlgorandLedger, build_algorand_ledger
from api.traceability.infrastructure.ledger import get_ledger

RECEIVER = account.generate_account()[1]


class AlgorandLedgerTests(SimpleTestCase):

    def setUp(self):
        self.private_key, self.sender = account.generate_account()
        self.algod = mock.Mock()
        self.algod.suggested_params.return_value = SuggestedParams(
            fee=1000, first=1, last=1000, gh=base64.b64encode(b'\x00' * 32).decode(), flat_fee=True,
        )
        self.algod.send_transaction.return_value = 'SUBMITTED_TX'
        self.ledger = AlgorandLedger(
            client=self.algod, sender=self.sender, private_key=self.private_key, receiver=RECEIVER,
        )
        patcher = mock.patch('api.traceability.infrastructure.algorand.transaction.wait_for_confirmation')
        self.wait_for_confirmation = patcher.start()
        self.addCleanup(patcher.stop)

    def test_records_a_signed_zero_amount_payment_carrying_the_note(self):
        tx_id = self.ledger.record('Quantity: 10')

        self.assertEqual(tx_id, 'SUBMITTED_TX')
        signed = self.algod.send_transaction.call_args.args[0]
        self.assertEqual(signed.transaction.sender, self.sender)
        self.assertEqual(signed.transaction.receiver, RECEIVER)
        self.assertEqual(signed.transaction.amt, 0)
        self.assertEqual(signed.transaction.note, b'Quantity: 10')
        self.wait_for_confirmation.assert_called_once_with(self.algod, 'SUBMITTED_TX', 4)

    def test_submission_failure_raises_ledger_unavailable(self):
        self.algod.send_transaction.side_effect = AlgodHTTPError('node unavailable')
        with self.assertRaises(LedgerUnavailable):
            self.ledger.record('Quantity: 10')

    def test_unreachable_node_raises_ledger_unavailable(self):
        self.algod.suggested_params.side_effect = ConnectionError('no route to host')
        with self.assertRaises(LedgerUnavailable):
            self.ledger.record('Quantity: 10')

    def test_confirmation_timeout_still_returns_the_submitted_id(self):
        self.wait_for_confirmation.side_effect = Exception('timeout')
        with self.assertLogs('api.traceability', level='WARNING'):
            self.assertEqual(self.ledger.record('Quantity: 10'), 'SUBMITTED_TX')


class AlgorandLedgerConfigurationTests(SimpleTestCase):

    @override_settings(
        ALGOD_ADDRESS='https://node.example.com', ALGOD_TOKEN='token',
        ALGORAND_SENDER='SENDER', ALGORAND_PRIVATE_KEY='KEY', ALGORAND_RECEIVER='RECEIVER',
    )
    def test_builds_the_ledger_from_settings(self):
        ledger = build_algorand_ledger()
        self.assertEqual(ledger.client.algod_address, 'https://node.example.com')
        self.assertEqual(ledger.client.algod_token, 'token')
        self.assertEqual((ledger.sender, ledger.private_key, ledger.receiver), ('SENDER', 'KEY', 'RECEIVER'))

    @override_settings(LEDGER_GATEWAY='api.traceability.tests.fakes.fake_ledger')
    def test_get_ledger_uses_the_configured_factory(self):
        from api.traceability.tests.fakes import FAKE_LEDGER
        self.assertIs(get_ledger(), FAKE_LEDGER)

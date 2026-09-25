import unittest

import httpx
from algosdk import account
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings

from api.traceability.domain.errors import LedgerRuleViolation, LedgerUnavailable
from api.traceability.domain.roles import Role
from api.traceability.infrastructure.algorand import AlgorandContractLedger, build_algorand_ledger, ledger_error_from
from api.traceability.infrastructure.ledger import get_ledger


def localnet_running():
    try:
        return httpx.get('http://localhost:4001/health', timeout=1).status_code == 200
    except httpx.HTTPError:
        return False


class LedgerErrorMappingTests(SimpleTestCase):

    # Format produced by algokit-utils; the excerpt also shows the next assertion ("lot retired").
    LOGIC_ERROR = (
        "Txn ABC had error 'Runtime error when executing Traceability (appId: 1017) in transaction 0: "
        "unknown lot' at PC 304 and Source Line 236:\n\n\t    box_len\n\t    bury 1\n"
        "\t    assert // unknown lot\t\t<-- Error\n\t    // assert self.lots[lot].active.native, \"lot retired\"\n"
    )

    def test_contract_assertions_become_rule_violations(self):
        error = ledger_error_from(Exception(self.LOGIC_ERROR))
        self.assertIsInstance(error, LedgerRuleViolation)
        self.assertEqual(error.rule, 'unknown lot')

    def test_reads_the_marked_line_when_the_header_is_missing(self):
        error = ledger_error_from(Exception('\t    assert // insufficient balance\t\t<-- Error\n\t    // "lot retired"'))
        self.assertEqual(error.rule, 'insufficient balance')

    def test_other_failures_mean_the_ledger_is_unavailable(self):
        self.assertIsInstance(ledger_error_from(ConnectionError('no route to host')), LedgerUnavailable)


class LedgerConfigurationTests(SimpleTestCase):

    @override_settings(
        ALGOD_ADDRESS='https://node.example.com', ALGOD_TOKEN='token',
        ALGORAND_APP_ID=1234, ALGORAND_PRIVATE_KEY=account.generate_account()[0],
    )
    def test_builds_the_contract_ledger_from_settings(self):
        ledger = build_algorand_ledger()
        self.assertIsInstance(ledger, AlgorandContractLedger)
        self.assertEqual(ledger.app_id, 1234)

    @override_settings(ALGORAND_APP_ID=None, ALGORAND_PRIVATE_KEY=account.generate_account()[0])
    def test_requires_the_app_id(self):
        with self.assertRaises(ImproperlyConfigured):
            build_algorand_ledger()

    @override_settings(LEDGER_GATEWAY='api.traceability.tests.fakes.fake_ledger')
    def test_get_ledger_uses_the_configured_factory(self):
        from api.traceability.tests.fakes import FAKE_LEDGER
        self.assertIs(get_ledger(), FAKE_LEDGER)


@unittest.skipUnless(localnet_running(), 'LocalNet is not running (uvx algokit localnet start)')
class ContractLedgerOnLocalNetTests(SimpleTestCase):
    """Runs the adapter against the compiled contract on LocalNet."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from algokit_utils import AlgoAmount, AlgorandClient, PaymentParams

        from contracts.deploy import deploy

        algorand = AlgorandClient.default_localnet()
        admin = algorand.account.random()
        dispenser = algorand.account.localnet_dispenser()
        algorand.send.payment(PaymentParams(sender=dispenser.address, receiver=admin.address, amount=AlgoAmount(algo=20)))
        app_id = deploy(algorand, admin.address, funding=AlgoAmount(algo=2)).app_id
        cls.ledger = AlgorandContractLedger(algorand=algorand, app_id=app_id, admin_private_key=admin.private_key)

    def actor(self, role):
        private_key, address = account.generate_account()
        self.ledger.register_actor(address, role)
        return private_key, address

    def test_full_lifecycle_and_rules(self):
        winery_key, _ = self.actor(Role.WINERY)
        distributor_key, distributor = self.actor(Role.DISTRIBUTOR)

        self.assertEqual(len(self.ledger.register_lot(winery_key, 1, 100)), 52)
        self.assertEqual(len(self.ledger.transfer(winery_key, 1, distributor, 30)), 52)

        with self.assertRaises(LedgerRuleViolation) as raised:
            self.ledger.transfer(distributor_key, 1, distributor, 1)
        self.assertEqual(raised.exception.rule, 'self transfer')

        with self.assertRaises(LedgerRuleViolation) as raised:
            self.ledger.transfer(winery_key, 1, distributor, 71)
        self.assertEqual(raised.exception.rule, 'insufficient balance')

        self.ledger.retire_lot(winery_key, 1)
        with self.assertRaises(LedgerRuleViolation) as raised:
            self.ledger.transfer(winery_key, 1, distributor, 1)
        self.assertEqual(raised.exception.rule, 'lot retired')

    def test_revoked_actors_are_frozen(self):
        winery_key, winery = self.actor(Role.WINERY)
        _, distributor = self.actor(Role.DISTRIBUTOR)
        self.ledger.register_lot(winery_key, 3, 10)

        self.assertEqual(len(self.ledger.revoke_actor(winery)), 52)

        with self.assertRaises(LedgerRuleViolation) as raised:
            self.ledger.transfer(winery_key, 3, distributor, 1)
        self.assertEqual(raised.exception.rule, 'unknown sender')

    def test_only_registered_actors_can_be_revoked(self):
        with self.assertRaises(LedgerRuleViolation) as raised:
            self.ledger.revoke_actor(account.generate_account()[1])
        self.assertEqual(raised.exception.rule, 'unknown actor')

    def test_only_wineries_register_lots(self):
        distributor_key, _ = self.actor(Role.DISTRIBUTOR)
        with self.assertRaises(LedgerRuleViolation) as raised:
            self.ledger.register_lot(distributor_key, 2, 10)
        self.assertEqual(raised.exception.rule, 'winery only')

    def test_unreachable_node_is_reported_as_unavailable(self):
        from algokit_utils import AlgoClientNetworkConfig, AlgorandClient

        offline = AlgorandClient.from_config(algod_config=AlgoClientNetworkConfig(server='http://localhost:1', token=''))
        ledger = AlgorandContractLedger(algorand=offline, app_id=self.ledger.app_id, admin_private_key=account.generate_account()[0])
        with self.assertRaises(LedgerUnavailable):
            ledger.register_actor(account.generate_account()[1], Role.WINERY)


@unittest.skipUnless(localnet_running(), 'LocalNet is not running (uvx algokit localnet start)')
class DeployCommandTests(SimpleTestCase):

    def test_deploys_a_funded_app_owned_by_the_admin_and_prints_its_id(self):
        import io

        from algokit_utils import AlgoAmount, AlgorandClient, PaymentParams
        from django.core.management import call_command

        algorand = AlgorandClient.default_localnet()
        admin = algorand.account.random()
        dispenser = algorand.account.localnet_dispenser()
        algorand.send.payment(PaymentParams(sender=dispenser.address, receiver=admin.address, amount=AlgoAmount(algo=5)))

        output = io.StringIO()
        with self.settings(ALGOD_ADDRESS='http://localhost:4001', ALGOD_TOKEN='a' * 64, ALGORAND_PRIVATE_KEY=admin.private_key):
            call_command('deploy_traceability', '--funding', '1.5', stdout=output)

        app_id = int(output.getvalue().strip().rsplit('ALGORAND_APP_ID=', 1)[1])
        app = algorand.app.get_by_id(app_id)
        self.assertEqual(app.creator, admin.address)
        self.assertEqual(algorand.account.get_information(app.app_address).amount.micro_algo, 1_500_000)

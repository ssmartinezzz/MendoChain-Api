from cryptography.fernet import Fernet
from django.contrib.auth.models import User
from django.test import TestCase

from api.traceability.application import selectors, services
from api.traceability.domain.errors import (
    LedgerRuleViolation,
    LedgerUnavailable,
    LegacyWine,
    NotAnActor,
    NotTheProducer,
    TransactionNotFound,
    WineNotFound,
    WineryOnly,
)
from api.traceability.domain.roles import Role
from api.traceability.infrastructure.key_vault import KeyVault
from api.traceability.models import Transaction, Wine
from api.traceability.tests.fakes import FakeLedger

WINE_DATA = {
    'variety_name': 'Malbec',
    'content': '750',
    'alcohol': '13.5',
    'brand_name': 'MendoWines',
    'lote': 'L-001',
    'year': '2020',
}


class ChainTestCase(TestCase):
    """Users with custodial actors, a fake ledger and a vault."""

    def setUp(self):
        self.ledger = FakeLedger()
        self.vault = KeyVault(Fernet.generate_key().decode())
        self.winery_user = self.actor_user('winery@test.com', Role.WINERY)
        self.distributor_user = self.actor_user('distributor@test.com', Role.DISTRIBUTOR)

    def actor_user(self, username, role):
        user = User.objects.create_user(username=username, password='pass12345!')
        services.register_actor(user=user, role=role, ledger=self.ledger, vault=self.vault)
        return user

    def register_wine(self, producer=None, total=100):
        return services.register_wine(
            {**WINE_DATA, 'total_quantity': total},
            producer=producer or self.winery_user, ledger=self.ledger, vault=self.vault,
        )

    def signer_of(self, user):
        return self.vault.decrypt(user.actor.encrypted_private_key)


class RegisterWineTests(ChainTestCase):

    def test_registers_the_lot_on_chain_signed_by_the_winery(self):
        wine = self.register_wine(total=120)

        self.assertEqual(wine.producer, self.winery_user.actor)
        self.assertEqual(wine.total_quantity, 120)
        self.assertTrue(wine.visibility)
        self.assertEqual(self.ledger.lots, [(self.signer_of(self.winery_user), wine.pk, 120)])

    def test_only_winery_actors_register_wines(self):
        with self.assertRaises(WineryOnly):
            self.register_wine(producer=self.distributor_user)
        self.assertFalse(Wine.objects.exists())

    def test_users_without_an_actor_cannot_register_wines(self):
        stranger = User.objects.create_user(username='stranger@test.com', password='pass12345!')
        with self.assertRaises(NotAnActor):
            self.register_wine(producer=stranger)

    def test_nothing_is_stored_when_the_ledger_fails(self):
        self.ledger.error = LedgerUnavailable('node down')
        with self.assertRaises(LedgerUnavailable):
            self.register_wine()
        self.assertFalse(Wine.objects.exists())


class UpdateAndRetireWineTests(ChainTestCase):

    def test_update_changes_the_description_but_not_the_lot(self):
        wine = self.register_wine(total=50)
        services.update_wine(wine.pk, {**WINE_DATA, 'brand_name': 'Andes'})
        wine.refresh_from_db()
        self.assertEqual((wine.brand_name, wine.total_quantity), ('Andes', 50))

    def test_the_producer_retires_the_lot_on_chain(self):
        wine = self.register_wine()
        services.retire_wine(wine.pk, by=self.winery_user, ledger=self.ledger, vault=self.vault)

        self.assertEqual(list(selectors.active_wines()), [])
        self.assertEqual(self.ledger.retired, [(self.signer_of(self.winery_user), wine.pk)])

    def test_only_the_producer_retires_an_on_chain_wine(self):
        wine = self.register_wine()
        with self.assertRaises(NotTheProducer):
            services.retire_wine(wine.pk, by=self.distributor_user, ledger=self.ledger, vault=self.vault)
        self.assertEqual(list(selectors.active_wines()), [wine])

    def test_legacy_wines_are_retired_off_chain(self):
        legacy = Wine.objects.create(**WINE_DATA)
        services.retire_wine(legacy.pk, by=self.distributor_user, ledger=self.ledger, vault=self.vault)
        self.assertEqual(list(selectors.active_wines()), [])
        self.assertEqual(self.ledger.retired, [])

    def test_retired_or_missing_wines_cannot_be_changed(self):
        wine = self.register_wine()
        services.retire_wine(wine.pk, by=self.winery_user, ledger=self.ledger, vault=self.vault)
        for wine_id in (wine.pk, 9999):
            with self.subTest(wine_id=wine_id):
                with self.assertRaises(WineNotFound):
                    services.update_wine(wine_id, WINE_DATA)
                with self.assertRaises(WineNotFound):
                    services.retire_wine(wine_id, by=self.winery_user, ledger=self.ledger, vault=self.vault)

    def test_retired_wines_stay_readable_by_id(self):
        wine = self.register_wine()
        services.retire_wine(wine.pk, by=self.winery_user, ledger=self.ledger, vault=self.vault)
        self.assertEqual(selectors.wine_by_id(wine.pk), wine)


class TransferBottlesTests(ChainTestCase):

    def setUp(self):
        super().setUp()
        self.wine = self.register_wine(total=100)

    def transfer(self, sender=None, recipient=None, quantity=10, wine=None):
        return services.transfer_bottles(
            wine=wine or self.wine,
            sender=sender or self.winery_user,
            recipient=recipient or self.distributor_user.actor,
            quantity=quantity,
            ledger=self.ledger,
            vault=self.vault,
        )

    def test_transfers_on_chain_signed_by_the_sender_and_stores_the_movement(self):
        movement = self.transfer(quantity=30)

        self.assertEqual(
            self.ledger.transfers,
            [(self.signer_of(self.winery_user), self.wine.pk, self.distributor_user.actor.address, 30)],
        )
        self.assertEqual(movement.sender, self.winery_user.actor)
        self.assertEqual(movement.recipient, self.distributor_user.actor)
        self.assertEqual(movement.quantity, 30)
        self.assertEqual(movement.transaction_id, 'FAKE_TRANSFER_TX_1')

    def test_contract_rule_violations_are_reported_and_nothing_is_stored(self):
        self.ledger.error = LedgerRuleViolation('insufficient balance')
        with self.assertRaises(LedgerRuleViolation):
            self.transfer(quantity=500)
        self.assertFalse(Transaction.objects.exists())

    def test_senders_must_be_actors(self):
        stranger = User.objects.create_user(username='stranger@test.com', password='pass12345!')
        with self.assertRaises(NotAnActor):
            self.transfer(sender=stranger)

    def test_legacy_wines_cannot_move(self):
        legacy = Wine.objects.create(**WINE_DATA)
        with self.assertRaises(LegacyWine):
            self.transfer(wine=legacy)
        self.assertEqual(self.ledger.transfers, [])

    def test_retire_movement_hides_it_once(self):
        movement = self.transfer()
        services.retire_movement(movement.pk)
        self.assertEqual(list(selectors.active_movements()), [])
        with self.assertRaises(TransactionNotFound):
            services.retire_movement(movement.pk)

    def test_movement_by_id_includes_retired_ones(self):
        movement = self.transfer()
        services.retire_movement(movement.pk)
        self.assertEqual(selectors.movement_by_id(movement.pk), movement)
        with self.assertRaises(TransactionNotFound):
            selectors.movement_by_id(9999)


class LedgerRuleViolationTests(TestCase):

    def test_uses_the_contract_rule_as_code(self):
        error = LedgerRuleViolation('insufficient balance')
        self.assertEqual(error.code, 'insufficient_balance')
        self.assertIn('insufficient balance', error.message)

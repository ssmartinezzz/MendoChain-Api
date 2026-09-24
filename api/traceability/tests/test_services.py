from django.test import TestCase

from api.traceability.application import selectors, services
from api.traceability.domain.errors import LedgerUnavailable, TransactionNotFound, WineNotFound
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


class WineServiceTests(TestCase):

    def test_register_wine_creates_an_active_wine(self):
        wine = services.register_wine(WINE_DATA)
        self.assertTrue(wine.visibility)
        self.assertEqual(Wine.objects.get().brand_name, 'MendoWines')

    def test_update_wine_changes_every_field(self):
        wine = services.register_wine(WINE_DATA)
        services.update_wine(wine.pk, {**WINE_DATA, 'brand_name': 'Andes'})
        wine.refresh_from_db()
        self.assertEqual(wine.brand_name, 'Andes')

    def test_retire_wine_hides_it(self):
        wine = services.register_wine(WINE_DATA)
        services.retire_wine(wine.pk)
        self.assertEqual(list(selectors.active_wines()), [])

    def test_retired_or_missing_wines_cannot_be_changed(self):
        wine = services.register_wine(WINE_DATA)
        services.retire_wine(wine.pk)
        for wine_id in (wine.pk, 9999):
            with self.subTest(wine_id=wine_id):
                with self.assertRaises(WineNotFound):
                    services.update_wine(wine_id, WINE_DATA)
                with self.assertRaises(WineNotFound):
                    services.retire_wine(wine_id)

    def test_retired_wines_stay_readable_by_id(self):
        wine = services.register_wine(WINE_DATA)
        services.retire_wine(wine.pk)
        self.assertEqual(selectors.wine_by_id(wine.pk), wine)
        with self.assertRaises(WineNotFound):
            selectors.wine_by_id(9999)


class RecordMovementTests(TestCase):

    def setUp(self):
        self.ledger = FakeLedger()
        self.wine = services.register_wine(WINE_DATA)

    def test_records_the_movement_on_the_ledger_and_stores_its_id(self):
        movement = services.record_movement(wine=self.wine, quantity=10, ledger=self.ledger)
        self.assertEqual(movement.transaction_id, 'FAKE_TX_1')
        self.assertEqual(movement.quantity, 10)
        self.assertTrue(movement.visibility)

    def test_ledger_note_keeps_the_on_chain_format(self):
        services.record_movement(wine=self.wine, quantity=10, ledger=self.ledger)
        self.assertEqual(
            self.ledger.notes[0],
            'Quantity: 10 \n Wine: Malbec  \n Alcohol: 13.5  \n Year: 2020  \n'
            'Content: 750  \n LotN° L-001 \n Brand: MendoWines',
        )

    def test_nothing_is_stored_when_the_ledger_fails(self):
        self.ledger.error = LedgerUnavailable('node down')
        with self.assertRaises(LedgerUnavailable):
            services.record_movement(wine=self.wine, quantity=10, ledger=self.ledger)
        self.assertFalse(Transaction.objects.exists())

    def test_retire_movement_hides_it_once(self):
        movement = services.record_movement(wine=self.wine, quantity=10, ledger=self.ledger)
        services.retire_movement(movement.pk)
        self.assertEqual(list(selectors.active_movements()), [])
        with self.assertRaises(TransactionNotFound):
            services.retire_movement(movement.pk)

    def test_movement_by_id_includes_retired_ones(self):
        movement = services.record_movement(wine=self.wine, quantity=10, ledger=self.ledger)
        services.retire_movement(movement.pk)
        self.assertEqual(selectors.movement_by_id(movement.pk), movement)
        with self.assertRaises(TransactionNotFound):
            selectors.movement_by_id(9999)

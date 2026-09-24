from django.contrib.auth.models import User
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from api.traceability.domain.errors import LedgerUnavailable
from api.traceability.models import Transaction, Wine
from api.traceability.tests.fakes import FAKE_LEDGER

FAKE_LEDGER_SETTING = 'api.traceability.tests.fakes.fake_ledger'

WINE_PAYLOAD = {
    'variety_name': 'Malbec',
    'content': '750',
    'alcohol': '13.5',
    'brand_name': 'MendoWines',
    'lote': 'L-001',
    'year': '2020',
}


class WineWritePermissionsTests(APITestCase):
    url = '/api/wine'

    def setUp(self):
        self.user = User.objects.create_user(username='user@test.com', password='pass12345!')

    def test_anonymous_cannot_create_wine(self):
        response = self.client.post(self.url, WINE_PAYLOAD)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(Wine.objects.exists())

    def test_registered_user_can_create_wine(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(self.url, WINE_PAYLOAD)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Wine.objects.count(), 1)

    def test_anonymous_can_list_wines(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


@override_settings(LEDGER_GATEWAY=FAKE_LEDGER_SETTING)
class TransactionWritePermissionsTests(APITestCase):
    url = '/api/transaction'

    def setUp(self):
        FAKE_LEDGER.reset()
        self.user = User.objects.create_user(username='user@test.com', password='pass12345!')
        self.wine = Wine.objects.create(**WINE_PAYLOAD)

    def test_anonymous_cannot_create_transaction(self):
        response = self.client.post(self.url, {'quantity': 10, 'wine': self.wine.pk})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(FAKE_LEDGER.notes, [])
        self.assertFalse(Transaction.objects.exists())

    def test_registered_user_can_create_transaction(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(self.url, {'quantity': 10, 'wine': self.wine.pk})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(FAKE_LEDGER.notes), 1)
        self.assertEqual(response.data, {
            'id': Transaction.objects.get().pk, 'quantity': 10,
            'transaction_id': 'FAKE_TX_1', 'wine': self.wine.pk, 'visibility': True,
        })


class WineUpdateAndDeleteTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='user@test.com', password='pass12345!')
        self.wine = Wine.objects.create(**WINE_PAYLOAD)
        self.url = f'/api/wine/{self.wine.pk}'
        self.client.force_authenticate(self.user)

    def test_put_updates_every_field_and_keeps_wine_visible(self):
        payload = {**WINE_PAYLOAD, 'variety_name': 'Cabernet', 'brand_name': 'Andes'}
        response = self.client.put(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.wine.refresh_from_db()
        self.assertEqual(self.wine.variety_name, 'Cabernet')
        self.assertEqual(self.wine.brand_name, 'Andes')
        self.assertTrue(self.wine.visibility)

    def test_visibility_cannot_be_set_by_clients(self):
        response = self.client.put(self.url, {**WINE_PAYLOAD, 'visibility': False})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.wine.refresh_from_db()
        self.assertTrue(self.wine.visibility)

    def test_delete_soft_deletes_wine(self):
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.wine.refresh_from_db()
        self.assertFalse(self.wine.visibility)
        self.assertEqual(self.client.get('/api/allwine').data, [])

    def test_deleted_wine_stays_retrievable_by_id(self):
        self.client.delete(self.url)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_deleted_wine_cannot_be_updated_or_deleted_again(self):
        self.client.delete(self.url)
        self.assertEqual(self.client.put(self.url, WINE_PAYLOAD).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.delete(self.url).status_code, status.HTTP_404_NOT_FOUND)

    def test_anonymous_cannot_delete_wine(self):
        self.client.force_authenticate(None)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_wine_returns_404(self):
        self.assertEqual(self.client.get('/api/wine/9999').status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.put('/api/wine/9999', WINE_PAYLOAD).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.delete('/api/wine/9999').status_code, status.HTTP_404_NOT_FOUND)


class TransactionUpdateAndDeleteTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='user@test.com', password='pass12345!')
        self.wine = Wine.objects.create(**WINE_PAYLOAD)
        self.transaction = Transaction.objects.create(quantity=10, transaction_id='TX1', wine=self.wine)
        self.url = f'/api/transaction/{self.transaction.pk}'
        self.client.force_authenticate(self.user)

    def test_transactions_cannot_be_edited(self):
        response = self.client.put(self.url, {'quantity': 99, 'wine': self.wine.pk, 'transaction_id': 'FORGED'})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.quantity, 10)
        self.assertEqual(self.transaction.transaction_id, 'TX1')
        self.assertTrue(self.transaction.visibility)

    def test_delete_soft_deletes_transaction(self):
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.transaction.refresh_from_db()
        self.assertFalse(self.transaction.visibility)

    def test_deleted_transaction_cannot_be_deleted_again(self):
        self.client.delete(self.url)
        self.assertEqual(self.client.delete(self.url).status_code, status.HTTP_404_NOT_FOUND)

    @override_settings(LEDGER_GATEWAY=FAKE_LEDGER_SETTING)
    def test_clients_cannot_choose_transaction_id(self):
        FAKE_LEDGER.reset()
        response = self.client.post('/api/transaction', {'quantity': 1, 'wine': self.wine.pk, 'transaction_id': 'FORGED'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['transaction_id'], 'FAKE_TX_1')


@override_settings(LEDGER_GATEWAY=FAKE_LEDGER_SETTING)
class TransactionInputTests(APITestCase):
    url = '/api/transaction'

    def setUp(self):
        FAKE_LEDGER.reset()
        self.user = User.objects.create_user(username='user@test.com', password='pass12345!')
        self.wine = Wine.objects.create(**WINE_PAYLOAD)
        self.client.force_authenticate(self.user)

    def test_ledger_failure_returns_502_and_records_nothing(self):
        FAKE_LEDGER.error = LedgerUnavailable('node unavailable')
        response = self.client.post(self.url, {'quantity': 1, 'wine': self.wine.pk})
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertEqual(response.json()['error']['code'], 'ledger_unavailable')
        self.assertFalse(Transaction.objects.exists())

    def test_quantity_must_be_positive(self):
        for quantity in (0, -5):
            with self.subTest(quantity=quantity):
                response = self.client.post(self.url, {'quantity': quantity, 'wine': self.wine.pk})
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn('quantity', response.json()['error']['details'])
        self.assertEqual(FAKE_LEDGER.notes, [])

    def test_unknown_wine_is_rejected_before_touching_the_ledger(self):
        response = self.client.post(self.url, {'quantity': 1, 'wine': 9999})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(FAKE_LEDGER.notes, [])


class WineInterfaceTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='user@test.com', password='pass12345!')
        self.client.force_authenticate(self.user)

    def test_all_wines_endpoint_is_read_only(self):
        response = self.client.post('/api/allwine', WINE_PAYLOAD)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertFalse(Wine.objects.exists())

    def test_create_returns_the_stored_wine(self):
        response = self.client.post('/api/wine', WINE_PAYLOAD)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data, {'id': Wine.objects.get().pk, **WINE_PAYLOAD, 'visibility': True})

    def test_list_is_paginated_and_hides_retired_wines(self):
        active = Wine.objects.create(**WINE_PAYLOAD)
        Wine.objects.create(**WINE_PAYLOAD, visibility=False)
        response = self.client.get('/api/wine')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], active.pk)

    def test_missing_wine_uses_domain_error_code(self):
        response = self.client.get('/api/wine/9999')
        self.assertEqual(response.json()['error']['code'], 'wine_not_found')

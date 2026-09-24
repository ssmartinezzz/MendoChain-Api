import base64
import os
from unittest import mock

from algosdk.error import AlgodHTTPError

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Transaction, Wine

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


@mock.patch('api.backend.serializers.first_transaction_example', return_value='FAKE_TX_ID')
class TransactionWritePermissionsTests(APITestCase):
    url = '/api/transaction'

    def setUp(self):
        self.user = User.objects.create_user(username='user@test.com', password='pass12345!')
        self.wine = Wine.objects.create(**WINE_PAYLOAD)

    def test_anonymous_cannot_create_transaction(self, send_to_blockchain):
        response = self.client.post(self.url, {'quantity': 10, 'wine': self.wine.pk})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        send_to_blockchain.assert_not_called()
        self.assertFalse(Transaction.objects.exists())

    def test_registered_user_can_create_transaction(self, send_to_blockchain):
        self.client.force_authenticate(self.user)
        response = self.client.post(self.url, {'quantity': 10, 'wine': self.wine.pk})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        send_to_blockchain.assert_called_once()
        self.assertEqual(Transaction.objects.get().transaction_id, 'FAKE_TX_ID')


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

    @mock.patch('api.backend.serializers.first_transaction_example', return_value='REAL_TX')
    def test_clients_cannot_choose_transaction_id(self, send_to_blockchain):
        response = self.client.post('/api/transaction', {'quantity': 1, 'wine': self.wine.pk, 'transaction_id': 'FORGED'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['transaction_id'], 'REAL_TX')


@mock.patch.dict('os.environ', {})
class TransactionBlockchainErrorTests(APITestCase):
    url = '/api/transaction'

    def setUp(self):
        from algosdk import account
        from algosdk.transaction import SuggestedParams

        private_key, address = account.generate_account()
        os.environ.update({'PRIVATE_KEY': private_key, 'WALLET_ADD': address})

        self.algod = mock.Mock()
        self.algod.account_info.return_value = {'amount': 1_000_000}
        self.algod.suggested_params.return_value = SuggestedParams(
            fee=1000, first=1, last=1000, gh=base64.b64encode(b'\x00' * 32).decode(), flat_fee=True,
        )
        patcher = mock.patch('api.backend.blockchain.algod.AlgodClient', return_value=self.algod)
        patcher.start()
        self.addCleanup(patcher.stop)

        self.user = User.objects.create_user(username='user@test.com', password='pass12345!')
        self.wine = Wine.objects.create(**WINE_PAYLOAD)
        self.client.force_authenticate(self.user)

    def test_submission_failure_returns_502_and_records_nothing(self):
        self.algod.send_transaction.side_effect = AlgodHTTPError('node unavailable')
        response = self.client.post(self.url, {'quantity': 1, 'wine': self.wine.pk})
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertFalse(Transaction.objects.exists())

    @mock.patch('api.backend.blockchain.transaction.wait_for_confirmation', side_effect=Exception('timeout'))
    def test_unconfirmed_submitted_transaction_is_still_recorded(self, wait_for_confirmation):
        self.algod.send_transaction.return_value = 'SUBMITTED_TX'
        response = self.client.post(self.url, {'quantity': 1, 'wine': self.wine.pk})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Transaction.objects.get().transaction_id, 'SUBMITTED_TX')

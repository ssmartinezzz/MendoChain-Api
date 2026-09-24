from unittest import mock

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

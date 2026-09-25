from cryptography.fernet import Fernet
from django.contrib.auth.models import User
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from api.traceability.application import services
from api.traceability.domain.errors import LedgerRuleViolation, LedgerUnavailable
from api.traceability.domain.roles import Role
from api.traceability.infrastructure.key_vault import get_key_vault
from api.traceability.models import Actor, Transaction, Wine
from api.traceability.tests.fakes import FAKE_LEDGER

WINE_PAYLOAD = {
    'variety_name': 'Malbec',
    'content': '750',
    'alcohol': '13.5',
    'brand_name': 'MendoWines',
    'lote': 'L-001',
    'year': '2020',
}
NEW_WINE = {**WINE_PAYLOAD, 'total_quantity': 100}


@override_settings(
    LEDGER_GATEWAY='api.traceability.tests.fakes.fake_ledger',
    ACTOR_KEYS_SECRET=Fernet.generate_key().decode(),
)
class ChainAPITestCase(APITestCase):
    """API tests against the in-memory ledger, with helpers to create actors."""

    def setUp(self):
        FAKE_LEDGER.reset()

    def user(self, username, role=None, **extra):
        user = User.objects.create_user(username=username, password='pass12345!', **extra)
        if role is not None:
            services.register_actor(user=user, role=role, ledger=FAKE_LEDGER, vault=get_key_vault())
        return user

    def on_chain_wine(self, producer, total=100):
        return services.register_wine(
            {**WINE_PAYLOAD, 'total_quantity': total}, producer=producer, ledger=FAKE_LEDGER, vault=get_key_vault(),
        )


class WineCreationTests(ChainAPITestCase):
    url = '/api/wine'

    def test_anonymous_cannot_create_wine(self):
        response = self.client.post(self.url, NEW_WINE)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(Wine.objects.exists())

    def test_a_winery_creates_a_wine_and_its_lot_on_chain(self):
        winery = self.user('winery@test.com', Role.WINERY)
        self.client.force_authenticate(winery)

        response = self.client.post(self.url, NEW_WINE)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        wine = Wine.objects.get()
        self.assertEqual(response.data, {
            'id': wine.pk, **WINE_PAYLOAD, 'visibility': True, 'total_quantity': 100, 'producer': winery.actor.pk,
        })
        self.assertEqual(len(FAKE_LEDGER.lots), 1)

    def test_users_without_an_actor_get_403(self):
        self.client.force_authenticate(self.user('user@test.com'))
        response = self.client.post(self.url, NEW_WINE)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.json()['error']['code'], 'not_an_actor')

    def test_only_wineries_create_wines(self):
        self.client.force_authenticate(self.user('dist@test.com', Role.DISTRIBUTOR))
        response = self.client.post(self.url, NEW_WINE)
        self.assertEqual(response.json()['error']['code'], 'winery_only')

    def test_total_quantity_is_required_and_positive(self):
        self.client.force_authenticate(self.user('winery@test.com', Role.WINERY))
        for payload in (WINE_PAYLOAD, {**WINE_PAYLOAD, 'total_quantity': 0}):
            with self.subTest(payload=payload):
                response = self.client.post(self.url, payload)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn('total_quantity', response.json()['error']['details'])

    def test_ledger_failure_returns_502_and_stores_nothing(self):
        self.client.force_authenticate(self.user('winery@test.com', Role.WINERY))
        FAKE_LEDGER.error = LedgerUnavailable('node down')
        response = self.client.post(self.url, NEW_WINE)
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertFalse(Wine.objects.exists())

    def test_anonymous_can_list_wines(self):
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_200_OK)

    def test_all_wines_endpoint_is_read_only(self):
        self.client.force_authenticate(self.user('winery@test.com', Role.WINERY))
        self.assertEqual(self.client.post('/api/allwine', NEW_WINE).status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_list_is_paginated_and_hides_retired_wines(self):
        active = Wine.objects.create(**WINE_PAYLOAD)
        Wine.objects.create(**WINE_PAYLOAD, visibility=False)
        response = self.client.get(self.url)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], active.pk)


class WineUpdateAndRetireTests(ChainAPITestCase):

    def setUp(self):
        super().setUp()
        self.winery = self.user('winery@test.com', Role.WINERY)
        self.wine = self.on_chain_wine(self.winery, total=40)
        self.url = f'/api/wine/{self.wine.pk}'
        self.client.force_authenticate(self.winery)

    def test_put_updates_the_description_but_not_the_lot(self):
        response = self.client.put(self.url, {**WINE_PAYLOAD, 'brand_name': 'Andes', 'total_quantity': 999})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.wine.refresh_from_db()
        self.assertEqual((self.wine.brand_name, self.wine.total_quantity), ('Andes', 40))

    def test_visibility_cannot_be_set_by_clients(self):
        self.client.put(self.url, {**WINE_PAYLOAD, 'visibility': False})
        self.wine.refresh_from_db()
        self.assertTrue(self.wine.visibility)

    def test_the_producer_retires_the_wine_on_chain(self):
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(FAKE_LEDGER.retired), 1)
        self.assertEqual(self.client.get('/api/allwine').data, [])

    def test_other_users_cannot_retire_an_on_chain_wine(self):
        self.client.force_authenticate(self.user('dist@test.com', Role.DISTRIBUTOR))
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.json()['error']['code'], 'producer_only')

    def test_legacy_wines_are_retired_by_any_registered_user(self):
        legacy = Wine.objects.create(**WINE_PAYLOAD)
        self.client.force_authenticate(self.user('user@test.com'))
        self.assertEqual(self.client.delete(f'/api/wine/{legacy.pk}').status_code, status.HTTP_204_NO_CONTENT)

    def test_retired_wines_stay_readable_but_cannot_change(self):
        self.client.delete(self.url)
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.put(self.url, WINE_PAYLOAD).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.delete(self.url).status_code, status.HTTP_404_NOT_FOUND)

    def test_anonymous_cannot_delete_wine(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.delete(self.url).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_wine_uses_domain_error_code(self):
        response = self.client.get('/api/wine/9999')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()['error']['code'], 'wine_not_found')


class TransferTests(ChainAPITestCase):
    url = '/api/transaction'

    def setUp(self):
        super().setUp()
        self.winery = self.user('winery@test.com', Role.WINERY)
        self.distributor = self.user('dist@test.com', Role.DISTRIBUTOR)
        self.wine = self.on_chain_wine(self.winery)
        self.client.force_authenticate(self.winery)

    def payload(self, **overrides):
        return {'wine': self.wine.pk, 'quantity': 10, 'recipient': self.distributor.actor.pk, **overrides}

    def test_anonymous_cannot_transfer(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.post(self.url, self.payload()).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(FAKE_LEDGER.transfers, [])

    def test_transfers_bottles_to_another_actor(self):
        response = self.client.post(self.url, self.payload(quantity=30))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        movement = Transaction.objects.get()
        self.assertEqual(response.data, {
            'id': movement.pk, 'quantity': 30, 'transaction_id': 'FAKE_TRANSFER_TX_1', 'wine': self.wine.pk,
            'visibility': True, 'sender': self.winery.actor.pk, 'recipient': self.distributor.actor.pk,
        })

    def test_clients_cannot_choose_the_transaction_id(self):
        response = self.client.post(self.url, self.payload(transaction_id='FORGED'))
        self.assertEqual(response.data['transaction_id'], 'FAKE_TRANSFER_TX_1')

    def test_contract_rule_violations_return_409_with_the_rule(self):
        FAKE_LEDGER.error = LedgerRuleViolation('insufficient balance')
        response = self.client.post(self.url, self.payload(quantity=500))
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.json()['error']['code'], 'insufficient_balance')
        self.assertFalse(Transaction.objects.exists())

    def test_ledger_failure_returns_502(self):
        FAKE_LEDGER.error = LedgerUnavailable('node down')
        response = self.client.post(self.url, self.payload())
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertEqual(response.json()['error']['code'], 'ledger_unavailable')

    def test_legacy_wines_cannot_move(self):
        legacy = Wine.objects.create(**WINE_PAYLOAD)
        response = self.client.post(self.url, self.payload(wine=legacy.pk))
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.json()['error']['code'], 'legacy_wine')

    def test_input_is_validated_before_touching_the_ledger(self):
        for overrides in ({'quantity': 0}, {'wine': 9999}, {'recipient': 9999}, {'recipient': ''}):
            with self.subTest(overrides=overrides):
                response = self.client.post(self.url, self.payload(**overrides))
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(FAKE_LEDGER.transfers, [])


class MovementRetirementTests(ChainAPITestCase):

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.user('user@test.com'))
        self.movement = Transaction.objects.create(quantity=10, transaction_id='TX1', wine=Wine.objects.create(**WINE_PAYLOAD))
        self.url = f'/api/transaction/{self.movement.pk}'

    def test_movements_cannot_be_edited(self):
        response = self.client.put(self.url, {'quantity': 99})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_soft_deletes_once(self):
        self.assertEqual(self.client.delete(self.url).status_code, status.HTTP_204_NO_CONTENT)
        self.movement.refresh_from_db()
        self.assertFalse(self.movement.visibility)
        self.assertEqual(self.client.delete(self.url).status_code, status.HTTP_404_NOT_FOUND)


class ActorsTests(ChainAPITestCase):
    url = '/api/actors'

    def test_admins_register_actors(self):
        admin = self.user('admin@test.com', is_staff=True)
        target = self.user('winery@test.com', first_name='Bodega Andes')
        self.client.force_authenticate(admin)

        response = self.client.post(self.url, {'user': target.pk, 'role': Role.WINERY})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        actor = Actor.objects.get()
        self.assertEqual(response.data, {'id': actor.pk, 'name': 'Bodega Andes', 'role': 'winery', 'address': actor.address})
        self.assertEqual(FAKE_LEDGER.actors, [(actor.address, Role.WINERY)])

    def test_only_admins_register_actors(self):
        target = self.user('winery@test.com')
        self.client.force_authenticate(self.user('user@test.com'))
        response = self.client.post(self.url, {'user': target.pk, 'role': Role.WINERY})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Actor.objects.exists())

    def test_registering_twice_returns_409(self):
        target = self.user('winery@test.com', Role.WINERY)
        self.client.force_authenticate(self.user('admin@test.com', is_staff=True))
        response = self.client.post(self.url, {'user': target.pk, 'role': Role.RETAILER})
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_rejects_unknown_roles(self):
        target = self.user('winery@test.com')
        self.client.force_authenticate(self.user('admin@test.com', is_staff=True))
        response = self.client.post(self.url, {'user': target.pk, 'role': 9})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_signed_in_users_list_actors_without_emails_or_keys(self):
        self.user('winery@test.com', Role.WINERY, first_name='Bodega Andes')
        self.client.force_authenticate(self.user('user@test.com'))

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([actor['name'] for actor in response.data], ['Bodega Andes'])
        self.assertEqual(set(response.data[0]), {'id', 'name', 'role', 'address'})

    def test_actors_without_a_first_name_are_listed_by_id(self):
        actor_user = self.user('winery@test.com', Role.WINERY)
        self.client.force_authenticate(actor_user)
        response = self.client.get(self.url)
        self.assertEqual(response.data[0]['name'], f'Actor {actor_user.actor.pk}')

    def test_anonymous_cannot_list_actors(self):
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_401_UNAUTHORIZED)


class AdminMembersTests(ChainAPITestCase):
    url = '/api/admin/members'
    member = {
        'email': 'bodega@test.com', 'password': 'Andes-2026-secure', 'first_name': 'Bodega',
        'last_name': 'Andes', 'role': Role.WINERY,
    }

    def setUp(self):
        super().setUp()
        self.admin = self.user('admin@test.com', is_staff=True)
        self.client.force_authenticate(self.admin)

    def test_onboards_a_member_with_its_on_chain_actor(self):
        response = self.client.post(self.url, self.member)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username='bodega@test.com')
        self.assertEqual(response.data, {
            'id': user.pk, 'email': 'bodega@test.com', 'name': 'Bodega Andes', 'is_staff': False,
            'actor': {'id': user.actor.pk, 'role': 'winery', 'address': user.actor.address, 'revoked': False},
        })
        self.assertEqual(FAKE_LEDGER.actors, [(user.actor.address, Role.WINERY)])

    def test_lists_every_user_with_its_actor(self):
        self.client.post(self.url, self.member)
        response = self.client.get(self.url)
        self.assertEqual([(m['email'], m['actor'] and m['actor']['role']) for m in response.data],
                         [('admin@test.com', None), ('bodega@test.com', 'winery')])

    def test_rejects_weak_passwords_and_bad_input(self):
        for overrides in ({'password': '123'}, {'email': 'not-an-email'}, {'role': 9}):
            with self.subTest(overrides=overrides):
                response = self.client.post(self.url, {**self.member, **overrides})
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(FAKE_LEDGER.actors, [])

    def test_duplicate_emails_return_409(self):
        self.client.post(self.url, self.member)
        response = self.client.post(self.url, {**self.member, 'email': 'BODEGA@test.com'})
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.json()['error']['code'], 'member_already_exists')

    def test_ledger_failure_returns_502_and_creates_no_user(self):
        FAKE_LEDGER.error = LedgerUnavailable('node down')
        self.assertEqual(self.client.post(self.url, self.member).status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertFalse(User.objects.filter(username='bodega@test.com').exists())

    def test_only_admins_use_the_panel(self):
        self.client.force_authenticate(self.user('user@test.com'))
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.post(self.url, self.member).status_code, status.HTTP_403_FORBIDDEN)


class RevokeActorAPITests(ChainAPITestCase):

    def setUp(self):
        super().setUp()
        self.winery = self.user('winery@test.com', Role.WINERY)
        self.distributor = self.user('dist@test.com', Role.DISTRIBUTOR)
        self.url = f'/api/actors/{self.distributor.actor.pk}'
        self.client.force_authenticate(self.user('admin@test.com', is_staff=True))

    def test_admins_revoke_actors_on_chain(self):
        self.assertEqual(self.client.delete(self.url).status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(FAKE_LEDGER.revoked_actors, [self.distributor.actor.address])
        self.assertEqual([a['name'] for a in self.client.get('/api/actors').data], [f'Actor {self.winery.actor.pk}'])

    def test_revoking_twice_or_unknown_actors(self):
        self.client.delete(self.url)
        self.assertEqual(self.client.delete(self.url).status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(self.client.delete('/api/actors/9999').status_code, status.HTTP_404_NOT_FOUND)

    def test_only_admins_revoke(self):
        self.client.force_authenticate(self.winery)
        self.assertEqual(self.client.delete(self.url).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(FAKE_LEDGER.revoked_actors, [])

    def test_revoked_actors_cannot_receive_bottles(self):
        wine = self.on_chain_wine(self.winery)
        self.client.delete(self.url)
        self.client.force_authenticate(self.winery)
        response = self.client.post('/api/transaction', {'wine': wine.pk, 'quantity': 1, 'recipient': self.distributor.actor.pk})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('recipient', response.json()['error']['details'])
        self.assertEqual(FAKE_LEDGER.transfers, [])

    def test_revoked_actors_get_403_when_acting(self):
        self.client.delete(f'/api/actors/{self.winery.actor.pk}')
        self.client.force_authenticate(self.winery)
        response = self.client.post('/api/wine', NEW_WINE)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.json()['error']['code'], 'actor_revoked')

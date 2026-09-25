from algosdk import account, encoding
from cryptography.fernet import Fernet
from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, TestCase, override_settings

from api.traceability.application import selectors, services
from api.traceability.domain.errors import (
    ActorAlreadyRegistered,
    ActorAlreadyRevoked,
    ActorNotFound,
    ActorRevoked,
    LedgerUnavailable,
    MemberAlreadyExists,
)
from api.traceability.domain.roles import Role
from api.traceability.infrastructure.key_vault import KeyVault, get_key_vault
from api.traceability.models import Actor
from api.traceability.tests.fakes import FakeLedger

SECRET = Fernet.generate_key().decode()


class KeyVaultTests(SimpleTestCase):

    def test_round_trips_a_private_key(self):
        vault = KeyVault(SECRET)
        private_key, _ = account.generate_account()
        encrypted = vault.encrypt(private_key)
        self.assertNotIn(private_key, encrypted)
        self.assertEqual(vault.decrypt(encrypted), private_key)

    def test_another_secret_cannot_decrypt(self):
        encrypted = KeyVault(SECRET).encrypt('secret-key')
        with self.assertRaises(ValueError):
            KeyVault(Fernet.generate_key().decode()).decrypt(encrypted)

    @override_settings(ACTOR_KEYS_SECRET='')
    def test_requires_a_configured_secret(self):
        with self.assertRaises(ImproperlyConfigured):
            get_key_vault()

    @override_settings(ACTOR_KEYS_SECRET=SECRET)
    def test_builds_from_settings(self):
        self.assertEqual(get_key_vault().decrypt(KeyVault(SECRET).encrypt('x')), 'x')


class RegisterActorTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='winery@test.com', password='pass12345!')
        self.ledger = FakeLedger()
        self.vault = KeyVault(SECRET)

    def register(self, user=None, role=Role.WINERY):
        return services.register_actor(user=user or self.user, role=role, ledger=self.ledger, vault=self.vault)

    def test_creates_an_algorand_account_for_the_user(self):
        actor = self.register()

        self.assertTrue(encoding.is_valid_address(actor.address))
        self.assertEqual(actor.role, Role.WINERY)
        self.assertEqual(Actor.objects.get().user, self.user)

    def test_stores_only_the_encrypted_key_and_it_matches_the_address(self):
        actor = self.register()

        private_key = self.vault.decrypt(actor.encrypted_private_key)
        self.assertNotEqual(actor.encrypted_private_key, private_key)
        self.assertEqual(account.address_from_private_key(private_key), actor.address)

    def test_registers_the_role_on_the_ledger(self):
        actor = self.register(role=Role.DISTRIBUTOR)
        self.assertEqual(self.ledger.actors, [(actor.address, Role.DISTRIBUTOR)])

    def test_nothing_is_stored_when_the_ledger_fails(self):
        self.ledger.error = LedgerUnavailable('node down')
        with self.assertRaises(LedgerUnavailable):
            self.register()
        self.assertFalse(Actor.objects.exists())

    def test_a_user_is_registered_only_once(self):
        self.register()
        with self.assertRaises(ActorAlreadyRegistered):
            self.register(role=Role.RETAILER)
        self.assertEqual(len(self.ledger.actors), 1)


class OnboardMemberTests(TestCase):

    def setUp(self):
        self.ledger = FakeLedger()
        self.vault = KeyVault(SECRET)

    def onboard(self, email='winery@test.com', role=Role.WINERY):
        return services.onboard_member(
            email=email, password='initial-pass-123', first_name='Bodega', last_name='Andes',
            role=role, ledger=self.ledger, vault=self.vault,
        )

    def test_creates_the_user_and_its_on_chain_actor(self):
        actor = self.onboard()

        user = User.objects.get()
        self.assertEqual((user.username, user.email, user.get_full_name()), ('winery@test.com', 'winery@test.com', 'Bodega Andes'))
        self.assertTrue(user.check_password('initial-pass-123'))
        self.assertEqual(actor.user, user)
        self.assertEqual(self.ledger.actors, [(actor.address, Role.WINERY)])

    def test_a_ledger_failure_leaves_no_user_behind(self):
        self.ledger.error = LedgerUnavailable('node down')
        with self.assertRaises(LedgerUnavailable):
            self.onboard()
        self.assertFalse(User.objects.exists())
        self.assertFalse(Actor.objects.exists())

    def test_rejects_an_email_already_in_use_without_touching_the_ledger(self):
        User.objects.create_user(username='winery@test.com', password='x')
        with self.assertRaises(MemberAlreadyExists):
            self.onboard()
        self.assertEqual(self.ledger.actors, [])


class RevokeActorTests(TestCase):

    def setUp(self):
        self.ledger = FakeLedger()
        self.vault = KeyVault(SECRET)
        self.actor = services.onboard_member(
            email='dist@test.com', password='initial-pass-123', first_name='Cuyo', last_name='',
            role=Role.DISTRIBUTOR, ledger=self.ledger, vault=self.vault,
        )

    def test_revokes_on_chain_and_marks_the_actor(self):
        services.revoke_actor(self.actor.pk, ledger=self.ledger)

        self.actor.refresh_from_db()
        self.assertIsNotNone(self.actor.revoked_at)
        self.assertEqual(self.ledger.revoked_actors, [self.actor.address])

    def test_revoked_actors_leave_the_recipient_list(self):
        services.revoke_actor(self.actor.pk, ledger=self.ledger)
        self.assertEqual(list(selectors.actors()), [])

    def test_a_ledger_failure_keeps_the_actor_active(self):
        self.ledger.error = LedgerUnavailable('node down')
        with self.assertRaises(LedgerUnavailable):
            services.revoke_actor(self.actor.pk, ledger=self.ledger)
        self.actor.refresh_from_db()
        self.assertIsNone(self.actor.revoked_at)

    def test_an_actor_is_revoked_only_once(self):
        services.revoke_actor(self.actor.pk, ledger=self.ledger)
        with self.assertRaises(ActorAlreadyRevoked):
            services.revoke_actor(self.actor.pk, ledger=self.ledger)
        self.assertEqual(len(self.ledger.revoked_actors), 1)

    def test_unknown_actors_cannot_be_revoked(self):
        with self.assertRaises(ActorNotFound):
            services.revoke_actor(9999, ledger=self.ledger)

    def test_revoked_actors_cannot_act_and_are_stopped_before_the_ledger(self):
        winery = services.onboard_member(
            email='winery@test.com', password='initial-pass-123', first_name='Andes', last_name='',
            role=Role.WINERY, ledger=self.ledger, vault=self.vault,
        )
        wine = services.register_wine(
            {'variety_name': 'Malbec', 'content': '750', 'alcohol': '13', 'brand_name': 'Andes',
             'lote': 'L1', 'year': '2020', 'total_quantity': 10},
            producer=winery.user, ledger=self.ledger, vault=self.vault,
        )
        services.revoke_actor(winery.pk, ledger=self.ledger)
        winery.user.refresh_from_db()

        with self.assertRaises(ActorRevoked):
            services.register_wine(
                {'variety_name': 'Syrah', 'content': '750', 'alcohol': '13', 'brand_name': 'Andes',
                 'lote': 'L2', 'year': '2020', 'total_quantity': 10},
                producer=winery.user, ledger=self.ledger, vault=self.vault,
            )
        with self.assertRaises(ActorRevoked):
            services.transfer_bottles(
                wine=wine, sender=winery.user, recipient=self.actor, quantity=1, ledger=self.ledger, vault=self.vault,
            )
        self.assertEqual(len(self.ledger.lots), 1)
        self.assertEqual(self.ledger.transfers, [])

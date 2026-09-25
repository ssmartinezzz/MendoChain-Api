from algosdk import account, encoding
from cryptography.fernet import Fernet
from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, TestCase, override_settings

from api.traceability.application import services
from api.traceability.domain.errors import ActorAlreadyRegistered, LedgerUnavailable
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

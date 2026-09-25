from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class KeyVault:
    """Encrypts custodial private keys at rest with a Fernet secret (AES-128-CBC + HMAC-SHA256)."""

    def __init__(self, secret):
        self._fernet = Fernet(secret)

    def encrypt(self, plaintext):
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, token):
        try:
            return self._fernet.decrypt(token.encode()).decode()
        except InvalidToken as err:
            raise ValueError('The key cannot be decrypted with the configured secret.') from err


def get_key_vault():
    if not settings.ACTOR_KEYS_SECRET:
        raise ImproperlyConfigured('ACTOR_KEYS_SECRET is required to manage custodial actor accounts.')
    return KeyVault(settings.ACTOR_KEYS_SECRET)

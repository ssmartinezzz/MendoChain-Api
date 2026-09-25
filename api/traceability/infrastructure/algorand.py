"""LedgerGateway backed by the Traceability contract on Algorand.

The admin account (the app creator) funds and registers actors. Every other call is signed with
the custodial key of the acting user, so the contract sees the real actor as sender and enforces
its rules on chain.
"""
import re
from pathlib import Path

from algokit_utils import (
    AlgoAmount,
    AlgoClientNetworkConfig,
    AlgorandClient,
    AppClient,
    AppClientMethodCallParams,
    AppClientParams,
    PaymentParams,
    SigningAccount,
)
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from api.traceability.domain.errors import LedgerRuleViolation, LedgerUnavailable

APP_SPEC = Path(settings.BASE_DIR) / 'contracts' / 'traceability' / 'build' / 'Traceability.arc56.json'

# Covers the 0.1 ALGO minimum balance of a new account plus fees for its first calls.
ACTOR_FUNDING = AlgoAmount(micro_algo=300_000)

# algokit-utils reports the failing assertion as "...in transaction N: <rule>' at PC"; the source
# excerpt that follows also contains neighbouring assertions, so the rule is read from that spot only.
_RULE_IN_HEADER = re.compile(r"in transaction \d+: ([a-z][a-z ]*)' at PC")
_RULE_AT_MARKER = re.compile(r'assert // ([a-z][a-z ]*?)\s*<-- Error')


def ledger_error_from(exc):
    """Translate an Algorand failure into a domain error."""
    message = str(exc)
    match = _RULE_IN_HEADER.search(message) or _RULE_AT_MARKER.search(message)
    if match:
        return LedgerRuleViolation(match.group(1).strip())
    return LedgerUnavailable(message)


class AlgorandContractLedger:

    def __init__(self, *, algorand, app_id, admin_private_key):
        self.algorand = algorand
        self.app_id = app_id
        self._admin = self._signer(admin_private_key)

    def register_actor(self, address, role):
        def send():
            funding = PaymentParams(sender=self._admin.address, receiver=address, amount=ACTOR_FUNDING)
            registration = self._app_client().params.call(
                AppClientMethodCallParams(method='register_actor', args=[address, int(role)], sender=self._admin.address)
            )
            return self.algorand.new_group().add_payment(funding).add_app_call_method_call(registration).send()

        return self._submit(send)

    def revoke_actor(self, address):
        return self._call('revoke_actor', [address], None)

    def register_lot(self, signer, lot, total):
        return self._call('register_lot', [lot, total], signer)

    def transfer(self, signer, lot, recipient, quantity):
        return self._call('transfer', [lot, recipient, quantity], signer)

    def retire_lot(self, signer, lot):
        return self._call('retire_lot', [lot], signer)

    def _call(self, method, args, private_key):
        """Call `method` signed by `private_key`, or by the admin when it is None."""
        sender = self._admin if private_key is None else self._signer(private_key)
        return self._submit(
            lambda: self._app_client().send.call(
                AppClientMethodCallParams(method=method, args=args, sender=sender.address)
            )
        )

    def _submit(self, send):
        try:
            result = send()
        except Exception as exc:
            raise ledger_error_from(exc) from exc
        return result.tx_ids[-1]

    def _signer(self, private_key):
        account = SigningAccount(private_key=private_key)
        self.algorand.account.set_signer_from_account(account)
        return account

    def _app_client(self):
        return AppClient(AppClientParams(app_spec=APP_SPEC.read_text('utf-8'), algorand=self.algorand, app_id=self.app_id))


def algorand_from_settings():
    return AlgorandClient.from_config(
        algod_config=AlgoClientNetworkConfig(server=settings.ALGOD_ADDRESS, token=settings.ALGOD_TOKEN),
    )


def admin_private_key():
    if not settings.ALGORAND_PRIVATE_KEY:
        raise ImproperlyConfigured('PRIVATE_KEY (the contract admin account) is required.')
    return settings.ALGORAND_PRIVATE_KEY


def build_algorand_ledger():
    if not settings.ALGORAND_APP_ID:
        raise ImproperlyConfigured('ALGORAND_APP_ID is required; deploy the contract with `manage.py deploy_traceability`.')
    return AlgorandContractLedger(
        algorand=algorand_from_settings(), app_id=int(settings.ALGORAND_APP_ID), admin_private_key=admin_private_key(),
    )

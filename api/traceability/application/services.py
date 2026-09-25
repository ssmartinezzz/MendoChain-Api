"""Write-side use cases.

Lots and movements are recorded on the traceability contract, signed by the custodial account of
the acting user. The database row is written in the same database transaction as the ledger call,
so a ledger failure leaves nothing behind. Movements mirror immutable ledger entries: they can be
retired from listings but never edited.
"""
from algosdk import account as algorand_account
from django.contrib.auth import get_user_model
from django.db import transaction as db_transaction
from django.utils import timezone

from api.traceability.domain.errors import (
    ActorAlreadyRegistered,
    ActorAlreadyRevoked,
    ActorNotFound,
    ActorRevoked,
    LegacyWine,
    MemberAlreadyExists,
    NotAnActor,
    NotTheProducer,
    TransactionNotFound,
    WineNotFound,
    WineryOnly,
)
from api.traceability.domain.roles import Role
from api.traceability.models import Actor, Transaction, Wine


def register_actor(*, user, role, ledger, vault):
    """Create a custodial Algorand account for `user` and register its role on the ledger first."""
    if Actor.objects.filter(user=user).exists():
        raise ActorAlreadyRegistered(user.pk)

    private_key, address = algorand_account.generate_account()
    ledger.register_actor(address, role)
    return Actor.objects.create(
        user=user,
        role=role,
        address=address,
        encrypted_private_key=vault.encrypt(private_key),
    )


def register_wine(data, *, producer, ledger, vault):
    """Store the wine and register its lot of bottles on chain, signed by the producing winery."""
    actor = _actor_of(producer)
    if actor.role != Role.WINERY:
        raise WineryOnly()

    with db_transaction.atomic():
        wine = Wine.objects.create(**data, producer=actor, visibility=True)
        ledger.register_lot(vault.decrypt(actor.encrypted_private_key), wine.pk, wine.total_quantity)
    return wine


def update_wine(wine_id, data):
    """Update the description. The lot size is fixed on chain and cannot change."""
    wine = _active_wine(wine_id)
    for field, value in data.items():
        setattr(wine, field, value)
    wine.save()
    return wine


def retire_wine(wine_id, *, by, ledger, vault):
    """Hide the wine. On-chain lots are retired by their producer so no more bottles can move."""
    wine = _active_wine(wine_id)
    actor = None
    if wine.producer_id is not None:
        actor = _actor_of(by)
        if actor.pk != wine.producer_id:
            raise NotTheProducer(wine.pk)

    with db_transaction.atomic():
        wine.visibility = False
        wine.save(update_fields=['visibility'])
        if actor is not None:
            ledger.retire_lot(vault.decrypt(actor.encrypted_private_key), wine.pk)


def transfer_bottles(*, wine, sender, recipient, quantity, ledger, vault):
    """Move bottles from `sender` to the `recipient` actor; the contract enforces balances and roles."""
    actor = _actor_of(sender)
    if wine.producer_id is None:
        raise LegacyWine(wine.pk)

    ledger_id = ledger.transfer(vault.decrypt(actor.encrypted_private_key), wine.pk, recipient.address, quantity)
    return Transaction.objects.create(
        wine=wine,
        quantity=quantity,
        transaction_id=ledger_id,
        sender=actor,
        recipient=recipient,
        visibility=True,
    )


def retire_movement(movement_id):
    movement = Transaction.objects.filter(pk=movement_id, visibility=True).first()
    if movement is None:
        raise TransactionNotFound(movement_id)
    movement.visibility = False
    movement.save(update_fields=['visibility'])


def _actor_of(user):
    """Active actor of `user`, read fresh so a revocation is never missed through a cached relation."""
    actor = Actor.objects.filter(user=user).first()
    if actor is None:
        raise NotAnActor(user.pk)
    if actor.revoked_at is not None:
        raise ActorRevoked(actor.pk)
    return actor


def _active_wine(wine_id):
    wine = Wine.objects.filter(pk=wine_id, visibility=True).first()
    if wine is None:
        raise WineNotFound(wine_id)
    return wine


def onboard_member(*, email, password, first_name, last_name, role, ledger, vault):
    """Create the user and its on-chain actor together: a ledger failure leaves no user behind."""
    User = get_user_model()
    if User.objects.filter(username__iexact=email).exists():
        raise MemberAlreadyExists(email)

    with db_transaction.atomic():
        user = User.objects.create_user(
            username=email, email=email, password=password, first_name=first_name, last_name=last_name,
        )
        return register_actor(user=user, role=role, ledger=ledger, vault=vault)


def revoke_actor(actor_id, *, ledger):
    """Remove the actor's role on chain, then mark it revoked so it can no longer operate."""
    actor = Actor.objects.filter(pk=actor_id).first()
    if actor is None:
        raise ActorNotFound(actor_id)
    if actor.revoked_at is not None:
        raise ActorAlreadyRevoked(actor_id)

    ledger.revoke_actor(actor.address)
    actor.revoked_at = timezone.now()
    actor.save(update_fields=['revoked_at'])
    return actor

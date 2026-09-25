"""Read-side queries. Retired records stay readable by id so history keeps resolving them."""
from django.contrib.auth import get_user_model

from api.traceability.domain.errors import TransactionNotFound, WineNotFound
from api.traceability.models import Actor, Transaction, Wine


def active_wines():
    return Wine.objects.filter(visibility=True).order_by('id')


def wine_by_id(wine_id):
    try:
        return Wine.objects.get(pk=wine_id)
    except Wine.DoesNotExist:
        raise WineNotFound(wine_id) from None


def active_movements():
    return Transaction.objects.filter(visibility=True).order_by('id')


def movement_by_id(movement_id):
    try:
        return Transaction.objects.get(pk=movement_id)
    except Transaction.DoesNotExist:
        raise TransactionNotFound(movement_id) from None


def actors():
    """Active actors: the possible recipients of a transfer."""
    return Actor.objects.filter(revoked_at__isnull=True).select_related('user').order_by('id')


def members():
    """Every user with its actor, if any, for the admin panel."""
    return get_user_model().objects.select_related('actor').order_by('id')

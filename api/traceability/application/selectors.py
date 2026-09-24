"""Read-side queries. Retired records stay readable by id so history keeps resolving them."""
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
    return Actor.objects.select_related('user').order_by('id')

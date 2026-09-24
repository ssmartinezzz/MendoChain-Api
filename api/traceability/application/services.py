"""Write-side use cases. Movements mirror immutable ledger entries, so they can be retired but not edited."""
from api.traceability.domain.errors import TransactionNotFound, WineNotFound
from api.traceability.models import Transaction, Wine


def register_wine(data):
    return Wine.objects.create(**data, visibility=True)


def update_wine(wine_id, data):
    wine = _active_wine(wine_id)
    for field, value in data.items():
        setattr(wine, field, value)
    wine.save()
    return wine


def retire_wine(wine_id):
    wine = _active_wine(wine_id)
    wine.visibility = False
    wine.save(update_fields=['visibility'])


def record_movement(*, wine, quantity, ledger):
    """Record the movement on the ledger first; it is stored only once the ledger accepted it."""
    ledger_id = ledger.record(_ledger_note(wine, quantity))
    return Transaction.objects.create(wine=wine, quantity=quantity, transaction_id=ledger_id, visibility=True)


def retire_movement(movement_id):
    movement = Transaction.objects.filter(pk=movement_id, visibility=True).first()
    if movement is None:
        raise TransactionNotFound(movement_id)
    movement.visibility = False
    movement.save(update_fields=['visibility'])


def _active_wine(wine_id):
    wine = Wine.objects.filter(pk=wine_id, visibility=True).first()
    if wine is None:
        raise WineNotFound(wine_id)
    return wine


def _ledger_note(wine, quantity):
    # Format already written on chain; keep it stable so existing entries stay comparable.
    return (
        f"Quantity: {quantity} \n "
        f"Wine: {wine.variety_name}  \n "
        f"Alcohol: {wine.alcohol}  \n "
        f"Year: {wine.year}  \n"
        f"Content: {wine.content}  \n "
        f"LotN° {wine.lote} \n "
        f"Brand: {wine.brand_name}"
    )

from django.conf import settings
from django.utils.module_loading import import_string


def get_ledger():
    """Build the LedgerGateway selected by the LEDGER_GATEWAY setting."""
    return import_string(settings.LEDGER_GATEWAY)()

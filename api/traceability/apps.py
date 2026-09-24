from django.apps import AppConfig


class TraceabilityConfig(AppConfig):
    name = 'api.traceability'
    # Keeps the original label so existing tables (backend_wine, backend_transaction) and migrations still apply.
    label = 'backend'

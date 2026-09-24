"""Create the Traceability app and fund its account for box storage."""
from pathlib import Path

from algokit_utils import AlgoAmount, AlgorandClient, AppClient, AppFactory, AppFactoryParams, PaymentParams

APP_SPEC = Path(__file__).parent / 'traceability' / 'build' / 'Traceability.arc56.json'


def deploy(algorand: AlgorandClient, admin: str, funding: AlgoAmount) -> AppClient:
    """Create a new app owned by `admin` (who becomes the contract admin) and fund it."""
    factory = AppFactory(AppFactoryParams(algorand=algorand, app_spec=APP_SPEC.read_text('utf-8'), default_sender=admin))
    app_client, _ = factory.send.bare.create()
    algorand.send.payment(PaymentParams(sender=admin, receiver=app_client.app_address, amount=funding))
    return app_client

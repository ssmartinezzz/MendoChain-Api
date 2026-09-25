from decimal import Decimal

from algokit_utils import AlgoAmount, SigningAccount
from django.core.management.base import BaseCommand

from api.traceability.infrastructure.algorand import admin_private_key, algorand_from_settings
from contracts.deploy import deploy


class Command(BaseCommand):
    help = 'Create the Traceability contract with the PRIVATE_KEY account as admin and fund it for box storage.'

    def add_arguments(self, parser):
        parser.add_argument('--funding', type=Decimal, default=Decimal('2'), help='ALGO sent to the app account (default: 2).')

    def handle(self, *args, funding, **options):
        algorand = algorand_from_settings()
        admin = SigningAccount(private_key=admin_private_key())
        algorand.account.set_signer_from_account(admin)

        app_client = deploy(algorand, admin.address, funding=AlgoAmount(micro_algo=int(funding * 1_000_000)))

        self.stdout.write(f'Deployed Traceability app {app_client.app_id} owned by {admin.address}.')
        self.stdout.write('Add this to your environment:')
        self.stdout.write(f'ALGORAND_APP_ID={app_client.app_id}')

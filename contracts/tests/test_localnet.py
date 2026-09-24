"""Runs the compiled contract on LocalNet (`uvx algokit localnet start`). Skipped when it is not running."""
import httpx
import pytest
from algokit_utils import AlgoAmount, AlgorandClient, AppClientMethodCallParams, PaymentParams

from contracts.deploy import deploy

WINERY, DISTRIBUTOR = 1, 2


def localnet_running() -> bool:
    try:
        return httpx.get('http://localhost:4001/health', timeout=1).status_code == 200
    except httpx.HTTPError:
        return False


pytestmark = pytest.mark.skipif(not localnet_running(), reason='LocalNet is not running')


@pytest.fixture()
def algorand() -> AlgorandClient:
    return AlgorandClient.default_localnet()


def funded_account(algorand: AlgorandClient, algo: int = 10):
    account = algorand.account.random()
    dispenser = algorand.account.localnet_dispenser()
    algorand.send.payment(PaymentParams(sender=dispenser.address, receiver=account.address, amount=AlgoAmount(algo=algo)))
    return account


def call(app_client, method, args, sender):
    return app_client.send.call(AppClientMethodCallParams(method=method, args=args, sender=sender.address))


def test_rules_are_enforced_by_the_compiled_contract(algorand):
    admin = funded_account(algorand)
    winery = funded_account(algorand, 1)
    distributor = funded_account(algorand, 1)

    app_client = deploy(algorand, admin.address, funding=AlgoAmount(algo=1))
    call(app_client, 'register_actor', [winery.address, WINERY], admin)
    call(app_client, 'register_actor', [distributor.address, DISTRIBUTOR], admin)

    call(app_client, 'register_lot', [7, 100], winery)
    result = call(app_client, 'transfer', [7, distributor.address, 60], winery)

    assert result.tx_ids
    assert call(app_client, 'balance_of', [7, winery.address], winery).abi_return == 40
    assert call(app_client, 'balance_of', [7, distributor.address], winery).abi_return == 60

    with pytest.raises(Exception, match='insufficient balance'):
        call(app_client, 'transfer', [7, winery.address, 61], distributor)


def test_deploy_funds_the_app_account_for_boxes(algorand):
    admin = funded_account(algorand)
    app_client = deploy(algorand, admin.address, funding=AlgoAmount(algo=1))

    info = algorand.account.get_information(app_client.app_address)
    assert info.amount.micro_algo == 1_000_000

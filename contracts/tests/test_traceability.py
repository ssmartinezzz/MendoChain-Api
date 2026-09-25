from collections.abc import Iterator

import pytest
from algopy import Account, UInt64, arc4
from algopy_testing import AlgopyTestContext, algopy_testing_context

from contracts.traceability.contract import DISTRIBUTOR, RETAILER, WINERY, Traceability

LOT = arc4.UInt64(7)


@pytest.fixture()
def context() -> Iterator[AlgopyTestContext]:
    with algopy_testing_context() as ctx:
        yield ctx


@pytest.fixture()
def contract(context: AlgopyTestContext) -> Traceability:
    return Traceability()


def as_sender(context: AlgopyTestContext, sender: Account):
    return context.txn.create_group(active_txn_overrides={"sender": sender})


def register(context: AlgopyTestContext, contract: Traceability, role: int) -> Account:
    account = context.any.account()
    contract.register_actor(arc4.Address(account), arc4.UInt8(role))
    return account


class TestActors:
    def test_admin_registers_actors_with_a_role(self, context, contract):
        winery = register(context, contract, WINERY)
        assert contract.role_of(arc4.Address(winery)) == WINERY

    def test_only_the_admin_registers_actors(self, context, contract):
        outsider = context.any.account()
        with pytest.raises(AssertionError, match="admin only"), as_sender(context, outsider):
            contract.register_actor(arc4.Address(outsider), arc4.UInt8(WINERY))

    def test_rejects_unknown_roles(self, context, contract):
        with pytest.raises(AssertionError, match="unknown role"):
            contract.register_actor(arc4.Address(context.any.account()), arc4.UInt8(9))

    def test_unregistered_accounts_have_no_role(self, context, contract):
        assert contract.role_of(arc4.Address(context.any.account())) == 0


class TestLots:
    def test_a_winery_registers_a_lot_and_holds_its_total(self, context, contract):
        winery = register(context, contract, WINERY)
        with as_sender(context, winery):
            contract.register_lot(LOT, arc4.UInt64(120))

        assert contract.balance_of(LOT, arc4.Address(winery)) == 120
        info = contract.lot_info(LOT)
        assert info.producer == arc4.Address(winery)
        assert info.total == 120
        assert info.active.native is True

    def test_only_wineries_register_lots(self, context, contract):
        distributor = register(context, contract, DISTRIBUTOR)
        with pytest.raises(AssertionError, match="winery only"), as_sender(context, distributor):
            contract.register_lot(LOT, arc4.UInt64(120))

    def test_a_lot_cannot_be_registered_twice(self, context, contract):
        winery = register(context, contract, WINERY)
        with as_sender(context, winery):
            contract.register_lot(LOT, arc4.UInt64(120))
        with pytest.raises(AssertionError, match="lot exists"), as_sender(context, winery):
            contract.register_lot(LOT, arc4.UInt64(50))

    def test_a_lot_needs_bottles(self, context, contract):
        winery = register(context, contract, WINERY)
        with pytest.raises(AssertionError, match="empty lot"), as_sender(context, winery):
            contract.register_lot(LOT, arc4.UInt64(0))


class TestTransfers:
    @pytest.fixture()
    def actors(self, context, contract):
        winery = register(context, contract, WINERY)
        distributor = register(context, contract, DISTRIBUTOR)
        retailer = register(context, contract, RETAILER)
        with as_sender(context, winery):
            contract.register_lot(LOT, arc4.UInt64(100))
        return winery, distributor, retailer

    def test_moves_bottles_along_the_chain(self, context, contract, actors):
        winery, distributor, retailer = actors
        with as_sender(context, winery):
            contract.transfer(LOT, arc4.Address(distributor), arc4.UInt64(60))
        with as_sender(context, distributor):
            contract.transfer(LOT, arc4.Address(retailer), arc4.UInt64(25))

        assert contract.balance_of(LOT, arc4.Address(winery)) == 40
        assert contract.balance_of(LOT, arc4.Address(distributor)) == 35
        assert contract.balance_of(LOT, arc4.Address(retailer)) == 25

    def test_cannot_move_more_than_held(self, context, contract, actors):
        winery, distributor, _ = actors
        with pytest.raises(AssertionError, match="insufficient balance"), as_sender(context, winery):
            contract.transfer(LOT, arc4.Address(distributor), arc4.UInt64(101))

    def test_cannot_move_bottles_of_someone_else(self, context, contract, actors):
        _, distributor, retailer = actors
        with pytest.raises(AssertionError, match="insufficient balance"), as_sender(context, distributor):
            contract.transfer(LOT, arc4.Address(retailer), arc4.UInt64(1))

    def test_quantity_must_be_positive(self, context, contract, actors):
        winery, distributor, _ = actors
        with pytest.raises(AssertionError, match="empty transfer"), as_sender(context, winery):
            contract.transfer(LOT, arc4.Address(distributor), arc4.UInt64(0))

    def test_recipient_must_be_a_registered_actor(self, context, contract, actors):
        winery, _, _ = actors
        stranger = context.any.account()
        with pytest.raises(AssertionError, match="unknown recipient"), as_sender(context, winery):
            contract.transfer(LOT, arc4.Address(stranger), arc4.UInt64(1))

    def test_cannot_transfer_to_yourself(self, context, contract, actors):
        winery, _, _ = actors
        with pytest.raises(AssertionError, match="self transfer"), as_sender(context, winery):
            contract.transfer(LOT, arc4.Address(winery), arc4.UInt64(1))

    def test_unknown_lots_cannot_be_moved(self, context, contract, actors):
        winery, distributor, _ = actors
        with pytest.raises(AssertionError, match="unknown lot"), as_sender(context, winery):
            contract.transfer(arc4.UInt64(999), arc4.Address(distributor), arc4.UInt64(1))


class TestRetirement:
    def test_the_producer_retires_a_lot_and_it_can_no_longer_move(self, context, contract):
        winery = register(context, contract, WINERY)
        distributor = register(context, contract, DISTRIBUTOR)
        with as_sender(context, winery):
            contract.register_lot(LOT, arc4.UInt64(10))
            contract.retire_lot(LOT)

        assert contract.lot_info(LOT).active.native is False
        with pytest.raises(AssertionError, match="lot retired"), as_sender(context, winery):
            contract.transfer(LOT, arc4.Address(distributor), arc4.UInt64(1))

    def test_only_the_producer_retires_a_lot(self, context, contract):
        winery = register(context, contract, WINERY)
        other_winery = register(context, contract, WINERY)
        with as_sender(context, winery):
            contract.register_lot(LOT, arc4.UInt64(10))
        with pytest.raises(AssertionError, match="producer only"), as_sender(context, other_winery):
            contract.retire_lot(LOT)


class TestRevocation:
    @pytest.fixture()
    def actors(self, context, contract):
        winery = register(context, contract, WINERY)
        distributor = register(context, contract, DISTRIBUTOR)
        with as_sender(context, winery):
            contract.register_lot(LOT, arc4.UInt64(100))
            contract.transfer(LOT, arc4.Address(distributor), arc4.UInt64(40))
        return winery, distributor

    def test_the_admin_revokes_a_role(self, context, contract, actors):
        _, distributor = actors
        contract.revoke_actor(arc4.Address(distributor))
        assert contract.role_of(arc4.Address(distributor)) == 0

    def test_only_the_admin_revokes(self, context, contract, actors):
        winery, distributor = actors
        with pytest.raises(AssertionError, match="admin only"), as_sender(context, winery):
            contract.revoke_actor(arc4.Address(distributor))

    def test_only_registered_accounts_can_be_revoked(self, context, contract):
        with pytest.raises(AssertionError, match="unknown actor"):
            contract.revoke_actor(arc4.Address(context.any.account()))

    def test_revoked_actors_cannot_send_their_bottles(self, context, contract, actors):
        winery, distributor = actors
        contract.revoke_actor(arc4.Address(distributor))
        with pytest.raises(AssertionError, match="unknown sender"), as_sender(context, distributor):
            contract.transfer(LOT, arc4.Address(winery), arc4.UInt64(1))

    def test_revoked_actors_cannot_receive(self, context, contract, actors):
        winery, distributor = actors
        contract.revoke_actor(arc4.Address(distributor))
        with pytest.raises(AssertionError, match="unknown recipient"), as_sender(context, winery):
            contract.transfer(LOT, arc4.Address(distributor), arc4.UInt64(1))

    def test_revoked_wineries_cannot_register_lots(self, context, contract, actors):
        winery, _ = actors
        contract.revoke_actor(arc4.Address(winery))
        with pytest.raises(AssertionError, match="winery only"), as_sender(context, winery):
            contract.register_lot(arc4.UInt64(8), arc4.UInt64(10))

    def test_balances_stay_on_chain_after_revocation(self, context, contract, actors):
        _, distributor = actors
        contract.revoke_actor(arc4.Address(distributor))
        assert contract.balance_of(LOT, arc4.Address(distributor)) == 40

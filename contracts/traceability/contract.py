"""Traceability contract: lots of bottles, balances per actor, and the rules for moving them.

The admin is the account that created the app. It registers actors with a role; wineries
register lots and receive their bottles; holders move bottles to other registered actors.
Every change emits an ARC-28 event so the full history can be read from the chain.

The app account must hold enough ALGO to cover the minimum balance of its boxes.
"""
from algopy import ARC4Contract, BoxMap, Bytes, Global, Txn, UInt64, arc4, op, subroutine

WINERY = 1
DISTRIBUTOR = 2
RETAILER = 3


class LotInfo(arc4.Struct):
    producer: arc4.Address
    total: arc4.UInt64
    active: arc4.Bool


class ActorRegistered(arc4.Struct):
    account: arc4.Address
    role: arc4.UInt8


class ActorRevoked(arc4.Struct):
    account: arc4.Address
    role: arc4.UInt8


class LotRegistered(arc4.Struct):
    lot: arc4.UInt64
    producer: arc4.Address
    total: arc4.UInt64


class Transferred(arc4.Struct):
    lot: arc4.UInt64
    sender: arc4.Address
    recipient: arc4.Address
    quantity: arc4.UInt64


class LotRetired(arc4.Struct):
    lot: arc4.UInt64
    producer: arc4.Address


@subroutine
def balance_key(lot: arc4.UInt64, account: arc4.Address) -> Bytes:
    return op.concat(lot.bytes, account.bytes)


class Traceability(ARC4Contract):
    def __init__(self) -> None:
        self.roles = BoxMap(arc4.Address, arc4.UInt8, key_prefix=b"a")
        self.lots = BoxMap(arc4.UInt64, LotInfo, key_prefix=b"l")
        # Key: lot id (8 bytes) + holder address (32 bytes).
        self.balances = BoxMap(Bytes, UInt64, key_prefix=b"b")

    @arc4.abimethod()
    def register_actor(self, account: arc4.Address, role: arc4.UInt8) -> None:
        assert Txn.sender == Global.creator_address, "admin only"
        assert role.as_uint64() >= WINERY and role.as_uint64() <= RETAILER, "unknown role"
        self.roles[account] = role
        arc4.emit(ActorRegistered(account, role))

    @arc4.abimethod()
    def revoke_actor(self, account: arc4.Address) -> None:
        """Remove the role: the account can no longer register lots, send or receive bottles."""
        assert Txn.sender == Global.creator_address, "admin only"
        assert account in self.roles, "unknown actor"
        role = self.roles[account]
        del self.roles[account]
        arc4.emit(ActorRevoked(account, role))

    @arc4.abimethod(readonly=True)
    def role_of(self, account: arc4.Address) -> UInt64:
        return self._role(account)

    @arc4.abimethod()
    def register_lot(self, lot: arc4.UInt64, total: arc4.UInt64) -> None:
        producer = arc4.Address(Txn.sender)
        assert self._role(producer) == WINERY, "winery only"
        assert lot not in self.lots, "lot exists"
        assert total.as_uint64() > 0, "empty lot"

        self.lots[lot] = LotInfo(producer, total, arc4.Bool(True))
        self.balances[balance_key(lot, producer)] = total.as_uint64()
        arc4.emit(LotRegistered(lot, producer, total))

    @arc4.abimethod()
    def transfer(self, lot: arc4.UInt64, to: arc4.Address, quantity: arc4.UInt64) -> None:
        sender = arc4.Address(Txn.sender)
        assert lot in self.lots, "unknown lot"
        assert self.lots[lot].active.native, "lot retired"
        assert self._role(sender) != 0, "unknown sender"
        assert quantity.as_uint64() > 0, "empty transfer"
        assert to != sender, "self transfer"
        assert self._role(to) != 0, "unknown recipient"

        sender_key = balance_key(lot, sender)
        held = self.balances.get(sender_key, default=UInt64(0))
        assert held >= quantity.as_uint64(), "insufficient balance"

        remaining = held - quantity.as_uint64()
        if remaining == 0:
            # Frees the box so its minimum balance returns to the app account.
            del self.balances[sender_key]
        else:
            self.balances[sender_key] = remaining

        recipient_key = balance_key(lot, to)
        self.balances[recipient_key] = self.balances.get(recipient_key, default=UInt64(0)) + quantity.as_uint64()
        arc4.emit(Transferred(lot, sender, to, quantity))

    @arc4.abimethod()
    def retire_lot(self, lot: arc4.UInt64) -> None:
        assert lot in self.lots, "unknown lot"
        info = self.lots[lot].copy()
        assert info.producer == arc4.Address(Txn.sender), "producer only"
        info.active = arc4.Bool(False)
        self.lots[lot] = info.copy()
        arc4.emit(LotRetired(lot, info.producer))

    @arc4.abimethod(readonly=True)
    def balance_of(self, lot: arc4.UInt64, account: arc4.Address) -> UInt64:
        return self.balances.get(balance_key(lot, account), default=UInt64(0))

    @arc4.abimethod(readonly=True)
    def lot_info(self, lot: arc4.UInt64) -> LotInfo:
        assert lot in self.lots, "unknown lot"
        return self.lots[lot]

    def _role(self, account: arc4.Address) -> UInt64:
        return self.roles.get(account, default=arc4.UInt8(0)).as_uint64()

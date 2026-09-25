class FakeLedger:
    """In-memory LedgerGateway for tests."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.actors = []
        self.revoked_actors = []
        self.lots = []
        self.transfers = []
        self.retired = []
        self.error = None

    def register_actor(self, address, role):
        if self.error:
            raise self.error
        self.actors.append((address, role))
        return f'FAKE_ACTOR_TX_{len(self.actors)}'

    def revoke_actor(self, address):
        if self.error:
            raise self.error
        self.revoked_actors.append(address)
        return f'FAKE_REVOKE_TX_{len(self.revoked_actors)}'

    def register_lot(self, signer, lot, total):
        if self.error:
            raise self.error
        self.lots.append((signer, lot, total))
        return f'FAKE_LOT_TX_{len(self.lots)}'

    def transfer(self, signer, lot, recipient, quantity):
        if self.error:
            raise self.error
        self.transfers.append((signer, lot, recipient, quantity))
        return f'FAKE_TRANSFER_TX_{len(self.transfers)}'

    def retire_lot(self, signer, lot):
        if self.error:
            raise self.error
        self.retired.append((signer, lot))
        return f'FAKE_RETIRE_TX_{len(self.retired)}'


FAKE_LEDGER = FakeLedger()


def fake_ledger():
    return FAKE_LEDGER

class FakeLedger:
    """In-memory LedgerGateway for tests."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.notes = []
        self.actors = []
        self.error = None

    def record(self, note):
        if self.error:
            raise self.error
        self.notes.append(note)
        return f'FAKE_TX_{len(self.notes)}'

    def register_actor(self, address, role):
        if self.error:
            raise self.error
        self.actors.append((address, role))
        return f'FAKE_ACTOR_TX_{len(self.actors)}'


FAKE_LEDGER = FakeLedger()


def fake_ledger():
    return FAKE_LEDGER

class FakeLedger:
    """In-memory LedgerGateway for tests."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.notes = []
        self.error = None

    def record(self, note):
        if self.error:
            raise self.error
        self.notes.append(note)
        return f'FAKE_TX_{len(self.notes)}'


FAKE_LEDGER = FakeLedger()


def fake_ledger():
    return FAKE_LEDGER

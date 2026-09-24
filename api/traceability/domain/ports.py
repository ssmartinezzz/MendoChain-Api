from typing import Protocol


class LedgerGateway(Protocol):
    """Append-only ledger where supply-chain movements are recorded."""

    def record(self, note: str) -> str:
        """Record `note` and return the ledger transaction id.

        Raises LedgerUnavailable when the entry could not be submitted.
        """

from typing import Protocol


class LedgerGateway(Protocol):
    """Append-only ledger where supply-chain movements are recorded."""

    def record(self, note: str) -> str:
        """Record `note` and return the ledger transaction id.

        Raises LedgerUnavailable when the entry could not be submitted.
        """

    def register_actor(self, address: str, role: int) -> str:
        """Fund `address` and grant it `role` on the ledger; return the transaction id.

        Raises LedgerUnavailable when it could not be completed.
        """

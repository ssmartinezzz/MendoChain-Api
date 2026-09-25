from typing import Protocol


class LedgerGateway(Protocol):
    """Ledger that enforces the supply-chain rules: actors, lots of bottles and transfers.

    `signer` is the private key of the acting actor. Every method returns the ledger transaction id
    and raises LedgerRuleViolation when a rule does not hold, or LedgerUnavailable when the ledger
    cannot be reached.
    """

    def register_actor(self, address: str, role: int) -> str:
        """Fund `address` and grant it `role`."""

    def register_lot(self, signer: str, lot: int, total: int) -> str:
        """Create lot `lot` with `total` bottles held by the signing winery."""

    def transfer(self, signer: str, lot: int, recipient: str, quantity: int) -> str:
        """Move `quantity` bottles of `lot` from the signer to `recipient`."""

    def retire_lot(self, signer: str, lot: int) -> str:
        """Stop further transfers of `lot`; only its producer can do it."""

from enum import IntEnum


class Role(IntEnum):
    """Supply-chain roles; values match the traceability contract."""

    WINERY = 1
    DISTRIBUTOR = 2
    RETAILER = 3

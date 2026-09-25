class DomainError(Exception):
    """Business error raised by services. It names a category, never an HTTP status."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


class NotFoundError(DomainError):
    """The requested resource does not exist or is no longer active."""


class UnavailableError(DomainError):
    """An external system the operation depends on could not complete it."""


class ConflictError(DomainError):
    """The operation clashes with the current state, e.g. something already exists."""


class ForbiddenError(DomainError):
    """The caller is not allowed to perform the operation."""

class SuperAdminError(Exception):
    """Base exception for super admin errors."""
    pass


class B2BRequestNotFoundError(SuperAdminError):
    """Raised when a B2B request cannot be found."""
    pass


class B2BRequestNotPendingError(SuperAdminError):
    """Raised when a B2B request is not in pending status."""
    pass


class InsufficientTicketsError(SuperAdminError):
    """Raised when not enough tickets are available."""

    def __init__(self, requested: int, available: int):
        self.requested = requested
        self.available = available
        super().__init__(f"Requested {requested} tickets, only {available} available")

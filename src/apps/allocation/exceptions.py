class AllocationError(Exception):
    """Base exception for allocation errors."""
    pass


class TicketHolderNotFoundError(AllocationError):
    """Raised when a ticket holder cannot be found."""
    pass


class TicketHolderInactiveError(AllocationError):
    """Raised when target holder is not active."""
    pass


class InsufficientTicketsError(AllocationError):
    """Raised when not enough unallocated tickets exist."""

    def __init__(self, requested: int, available: int):
        self.requested = requested
        self.available = available
        super().__init__(f"Requested {requested} tickets, only {available} available")


class AllocationLockError(AllocationError):
    """Raised when ticket lock acquisition fails."""
    pass


class AllocationOwnershipError(AllocationError):
    """Raised when ownership check fails during allocation."""
    pass


class AllocationStatusTransitionError(AllocationError):
    """Raised when an allocation status transition fails."""
    pass

import constants
from exceptions import AlreadyExistsError, BadRequestError, ForbiddenError, NotFoundError, UnprocessableEntityError


class OrganizerOwnershipError(ForbiddenError):
    message = "Organizer does not belong to current user."


class EventNotFound(NotFoundError):
    message = "Event not found."


class InvalidScanTransition(UnprocessableEntityError):
    message = "Invalid scan state transition."


class CannotPublishEvent(UnprocessableEntityError):
    message = "Event cannot be published due to validation errors."


class InvalidAsset(UnprocessableEntityError):
    message = "Invalid asset or asset does not belong to this event."


class ValidationError(UnprocessableEntityError):
    message = "Validation error."


class InsufficientTicketsError(BadRequestError):
    def __init__(self, requested: int, available: int):
        self.requested = requested
        self.available = available
        super().__init__(f"Not enough tickets available. Only {available} ticket(s) remaining for this selection.")


# Re-export for convenience
AlreadyExistsError = AlreadyExistsError

import constants
from exceptions import ForbiddenError, NotFoundError, UnprocessableEntityError


class OrganizerOwnershipError(ForbiddenError):
    message = "Organizer does not belong to current user."


class EventNotFound(NotFoundError):
    message = "Event not found."


class InvalidScanTransition(UnprocessableEntityError):
    message = "Invalid scan state transition."

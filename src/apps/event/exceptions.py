import constants
from exceptions import ForbiddenError, NotFoundError, UnprocessableEntityError


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

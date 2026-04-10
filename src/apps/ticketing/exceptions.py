import constants
from exceptions import BadRequestError, NotFoundError, UnprocessableEntityError


class OpenEventDoesNotSupportTickets(UnprocessableEntityError):
    message = "Open events do not support tickets."


class TicketTypeNotFound(NotFoundError):
    message = "Ticket type not found."


class InvalidPrice(BadRequestError):
    message = "Price must be non-negative."


class InvalidQuantity(BadRequestError):
    message = "Allocation quantity must be greater than 0."


class DuplicateAllocation(UnprocessableEntityError):
    message = "Ticket type is already allocated to this day."


class InvalidAllocation(UnprocessableEntityError):
    message = "Invalid ticket allocation."

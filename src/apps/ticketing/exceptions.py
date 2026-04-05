import constants
from exceptions import NotFoundError, UnprocessableEntityError


class OpenEventDoesNotSupportTickets(UnprocessableEntityError):
    message = "Open events do not support tickets."


class TicketTypeNotFound(NotFoundError):
    message = "Ticket type not found."

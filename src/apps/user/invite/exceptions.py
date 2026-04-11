from exceptions import NotFoundError, AlreadyExistsError, ForbiddenError


class InviteNotFound(NotFoundError):
    message = "Invite not found."


class InviteAlreadyProcessed(AlreadyExistsError):
    message = "Invite has already been processed."


class NotInviteRecipient(ForbiddenError):
    message = "You are not the recipient of this invite."
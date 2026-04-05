from exceptions import AlreadyExistsError, NotFoundError


class OrganizerSlugAlreadyExists(AlreadyExistsError):
    message = "Organizer slug already exists."


class OrganizerNotFound(NotFoundError):
    message = "Organizer page not found."

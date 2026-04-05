import constants
from exceptions import AlreadyExistsError


class OrganizerSlugAlreadyExists(AlreadyExistsError):
    message = "Organizer slug already exists."

import constants
from exceptions import CustomException, NotFoundError, UnauthorizedError, BadRequestError


class GuestNotFoundException(NotFoundError):
    message = "Guest not found"


class GuestAlreadyConvertedException(UnauthorizedError):
    message = "Guest has already been converted to a user"


class DuplicateEmailException(BadRequestError):
    message = "Email already registered"


class DuplicatePhoneException(BadRequestError):
    message = "Phone number already registered"

EMAIL_REGEX = r"^[a-zA-Z0-9._%+-]+(?<!\.)@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}$"

# Supports Indian mobile numbers (+91XXXXXXXXXX) and general international formats (E.164)
PHONE_REGEX = r"^(\+91[- ]?)?[6-9]\d{9}$"

FIRST_NAME_REGEX = r"^\S+\S$"
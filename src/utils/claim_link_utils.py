import secrets
import string


def generate_claim_link_token(length: int = 8) -> str:
    """
    Generate a cryptographically random 8-char alphanumeric token.
    Uses ASCII letters and digits for readability.
    """
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))

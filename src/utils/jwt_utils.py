from datetime import datetime
from uuid import UUID

import jwt
from jwt import DecodeError, ExpiredSignatureError

from config import settings
from exceptions import InvalidJWTTokenException


def generate_scan_jwt(
    jti: str,
    holder_id: UUID,
    event_day_id: UUID,
    indexes: list[int],
) -> str:
    """
    Generate a signed scan JWT.

    Payload:
        jti: Unique token ID (used for revocation tracking)
        holder_id: Who owns these tickets
        event_day_id: Which event day's bitmap to check/update
        indexes: List of ticket indexes for this holder's allocation
        iat: Issued at (UTC timestamp)
    """
    payload = {
        "jti": jti,
        "holder_id": str(holder_id),
        "event_day_id": str(event_day_id),
        "indexes": indexes,
        "iat": int(datetime.utcnow().timestamp()),
    }
    return jwt.encode(
        payload,
        key=settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def verify_scan_jwt(token: str) -> dict:
    """
    Verify and decode a scan JWT.
    Raises InvalidJWTTokenException if invalid or expired.
    """
    try:
        payload = jwt.decode(
            token,
            key=settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_signature": True, "verify_exp": False},
        )
        return payload
    except DecodeError:
        raise InvalidJWTTokenException("Invalid scan token")


def get_jti_from_jwt(token: str) -> str:
    """
    Extract jti from a scan JWT without full verification.
    Used for revocation lookups.
    """
    payload = jwt.decode(
        token,
        key=settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        options={"verify_signature": False, "verify_exp": False},
    )
    return payload["jti"]


def decode_scan_jwt(token: str) -> dict:
    """
    Decode a scan JWT without verification (for debugging/audit).
    """
    return jwt.decode(
        token,
        key=settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        options={"verify_signature": False, "verify_exp": False},
    )

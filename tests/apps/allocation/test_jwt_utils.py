import pytest
from uuid import uuid4
from src.utils.jwt_utils import (
    generate_scan_jwt,
    verify_scan_jwt,
    get_jti_from_jwt,
    decode_scan_jwt,
)
from exceptions import InvalidJWTTokenException


def test_generate_scan_jwt_returns_string():
    jti = "abc12345"
    holder_id = uuid4()
    event_day_id = uuid4()
    indexes = [0, 1, 2, 3, 4]

    token = generate_scan_jwt(jti, holder_id, event_day_id, indexes)
    assert isinstance(token, str)
    assert len(token) > 0


def test_verify_scan_jwt_returns_payload():
    jti = "abc12345"
    holder_id = uuid4()
    event_day_id = uuid4()
    indexes = [0, 1, 2]

    token = generate_scan_jwt(jti, holder_id, event_day_id, indexes)
    payload = verify_scan_jwt(token)

    assert payload["jti"] == jti
    assert payload["holder_id"] == str(holder_id)
    assert payload["event_day_id"] == str(event_day_id)
    assert payload["indexes"] == indexes


def test_get_jti_from_jwt_extracts_jti():
    jti = "test_jti_123"
    holder_id = uuid4()
    event_day_id = uuid4()

    token = generate_scan_jwt(jti, holder_id, event_day_id, [0, 1])
    extracted = get_jti_from_jwt(token)

    assert extracted == jti


def test_decode_scan_jwt_without_verification():
    jti = "decode_test"
    holder_id = uuid4()
    event_day_id = uuid4()
    indexes = [5, 6, 7]

    token = generate_scan_jwt(jti, holder_id, event_day_id, indexes)
    payload = decode_scan_jwt(token)

    assert payload["jti"] == jti
    assert payload["indexes"] == indexes


def test_verify_scan_jwt_rejects_invalid_token():
    with pytest.raises(InvalidJWTTokenException):
        verify_scan_jwt("not.a.valid.token")

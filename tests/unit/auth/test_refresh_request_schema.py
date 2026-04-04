from auth.schemas import RefreshRequest, RefreshRequestWithJti


def test_refresh_request_accepts_camel_case():
    body = RefreshRequest.model_validate({"refreshToken": "refresh-123"})
    assert body.refresh_token == "refresh-123"


def test_refresh_request_with_jti_accepts_camel_case():
    body = RefreshRequestWithJti.model_validate(
        {"refreshToken": "refresh-123", "accessTokenJti": "jti-456"}
    )
    assert body.refresh_token == "refresh-123"
    assert body.access_token_jti == "jti-456"

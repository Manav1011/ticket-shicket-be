from apps.user.models import RefreshTokenModel


def test_uuid_primary_key_default_is_callable():
    assert callable(RefreshTokenModel.__table__.c.id.default.arg)

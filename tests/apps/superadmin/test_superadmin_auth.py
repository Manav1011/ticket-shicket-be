import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from fastapi import Request


@pytest.fixture
def mock_admin():
    from apps.superadmin.models import SuperAdminModel
    admin = MagicMock(spec=SuperAdminModel)
    admin.id = uuid4()
    admin.user_id = uuid4()
    admin.name = "Test Admin"
    return admin


async def test_get_current_super_admin_sets_request_state(mock_admin):
    """get_current_super_admin should set request.state.super_admin AND return the admin."""
    from auth.dependencies import get_current_super_admin
    from fastapi.security import HTTPAuthorizationCredentials

    mock_credentials = MagicMock(spec=HTTPAuthorizationCredentials)
    mock_credentials.credentials = "valid_token"

    mock_session = AsyncMock()
    mock_session.scalar = AsyncMock(return_value=mock_admin)

    mock_request = MagicMock(spec=Request)
    mock_request.state = MagicMock()

    # Patch access.decode to return a valid payload
    import auth.dependencies as auth_deps
    original_decode = auth_deps.access.decode
    auth_deps.access.decode = MagicMock(return_value={"sub": str(mock_admin.user_id), "user_type": "user"})

    try:
        result = await get_current_super_admin(request=mock_request, credentials=mock_credentials, session=mock_session)

        assert result == mock_admin
        assert hasattr(mock_request.state, "super_admin")
        assert mock_request.state.super_admin == mock_admin
    finally:
        auth_deps.access.decode = original_decode

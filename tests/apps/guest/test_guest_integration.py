"""
Integration tests for Guest Module - Full Flow

These tests document the complete guest lifecycle:
1. Guest login - creates guest, returns device_id
2. Guest browse (protected endpoint) - uses guest token
3. Guest refresh - rotates tokens
4. Guest convert - creates user, marks guest converted
5. Guest token now invalid after conversion

Run with: pytest tests/apps/guest/test_guest_integration.py -v

Note: These tests require a running PostgreSQL database with the guest tables
created via migrations. They are designed to run against a test database.
"""
import pytest
from uuid import uuid4


class TestGuestFullLifecycle:
    """
    Integration test covering complete guest lifecycle.

    This test class documents the expected behavior of the guest module.
    To run these tests, ensure:
    1. Database migrations have been applied (python main.py migrate)
    2. Test database is available and configured in .env
    3. Redis is running for rate limiting
    """

    @pytest.mark.asyncio
    async def test_guest_login_returns_device_id_and_tokens(self, async_test_client):
        """
        Step 1: Guest login creates guest record and returns tokens.

        Expected:
        - POST /api/guest/login with X-Device-ID header
        - Returns: guest_id, device_id, access_token, refresh_token
        - Guest record created in database
        """
        device_id = str(uuid4())

        response = async_test_client.post(
            "/api/guest/login",
            headers={"X-Device-ID": device_id},
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert "guest_id" in data
        assert "device_id" in data
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["device_id"] == device_id

    @pytest.mark.asyncio
    async def test_guest_protected_endpoint_requires_token(self, async_test_client):
        """
        Step 2: Guest protected endpoints require valid token.

        Expected:
        - GET /api/guest/self without token returns 401
        - GET /api/guest/self with valid token returns guest info
        """
        response = async_test_client.get("/api/guest/self")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_guest_convert_creates_user_and_invalidates_guest(self, async_test_client):
        """
        Step 3: Guest conversion creates User, links Guest, returns new tokens.

        Expected:
        - POST /api/guest/convert with guest token and user details
        - Creates new User record
        - Marks Guest as is_converted=True with converted_user_id
        - Revokes all guest refresh tokens
        - Returns new user tokens
        """
        # First login as guest
        device_id = str(uuid4())
        login_response = async_test_client.post(
            "/api/guest/login",
            headers={"X-Device-ID": device_id},
        )
        guest_token = login_response.json()["data"]["access_token"]

        # Convert to user
        convert_response = async_test_client.post(
            "/api/guest/convert",
            headers={"Authorization": f"Bearer {guest_token}"},
            json={
                "email": "newuser@example.com",
                "phone": "+919876543210",
                "password": "SecurePassword123",
                "firstName": "John",
                "lastName": "Doe",
            },
        )

        assert convert_response.status_code == 200
        data = convert_response.json()["data"]
        assert "user_id" in data
        assert "access_token" in data
        assert "refresh_token" in data

        # Guest token should now be invalid
        guest_info_response = async_test_client.get(
            "/api/guest/self",
            headers={"Authorization": f"Bearer {guest_token}"},
        )
        assert guest_info_response.status_code == 401

    @pytest.mark.asyncio
    async def test_guest_token_refresh_rotates_tokens(self, async_test_client):
        """
        Step 4: Guest token refresh rotates the token pair.

        Expected:
        - POST /api/guest/refresh with valid refresh token
        - Returns new access_token and refresh_token
        - Old refresh token is revoked
        """
        # Login as guest
        device_id = str(uuid4())
        login_response = async_test_client.post(
            "/api/guest/login",
            headers={"X-Device-ID": device_id},
        )
        old_refresh_token = login_response.json()["data"]["refresh_token"]

        # Refresh tokens
        refresh_response = async_test_client.post(
            "/api/guest/refresh",
            json={"refreshToken": old_refresh_token},
        )

        assert refresh_response.status_code == 200
        data = refresh_response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["refresh_token"] != old_refresh_token

        # Old token should be revoked
        refresh_again = async_test_client.post(
            "/api/guest/refresh",
            json={"refreshToken": old_refresh_token},
        )
        assert refresh_again.status_code == 401

    @pytest.mark.asyncio
    async def test_guest_logout_revokes_token(self, async_test_client):
        """
        Step 5: Guest logout revokes the refresh token.

        Expected:
        - POST /api/guest/logout with refresh token
        - Token is revoked
        - Subsequent refresh with same token fails
        """
        # Login as guest
        device_id = str(uuid4())
        login_response = async_test_client.post(
            "/api/guest/login",
            headers={"X-Device-ID": device_id},
        )
        refresh_token = login_response.json()["data"]["refresh_token"]

        # Logout
        logout_response = async_test_client.post(
            "/api/guest/logout",
            json={"refreshToken": refresh_token},
        )
        assert logout_response.status_code == 200

        # Token should be revoked
        refresh_response = async_test_client.post(
            "/api/guest/refresh",
            json={"refreshToken": refresh_token},
        )
        assert refresh_response.status_code == 401


# Pytest fixture for test client would be defined in conftest.py:
#
# @pytest.fixture
# async def async_test_client():
#     """Provides an async test client with database setup."""
#     from httpx import AsyncClient
#     from server import create_app
#
#     app = create_app()
#     async with AsyncClient(app=app, base_url="http://test") as client:
#         yield client

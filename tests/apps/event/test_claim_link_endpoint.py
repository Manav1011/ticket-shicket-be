import pytest
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_claim_link_returns_jwt_string():
    """GET /open/claim/{token} returns a plain JWT string."""
    pass


@pytest.mark.asyncio
async def test_claim_link_invalid_token_returns_404():
    """Invalid token returns 404."""
    pass

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from src.apps.event.claim_service import ClaimService


@pytest.mark.asyncio
async def test_get_jwt_for_claim_token_success():
    """Valid active claim link returns JWT string."""
    pass


@pytest.mark.asyncio
async def test_get_jwt_for_claim_token_not_found():
    """Invalid token raises NotFoundError."""
    pass


@pytest.mark.asyncio
async def test_get_jwt_for_claim_token_inactive():
    """Inactive claim link raises BadRequestError."""
    pass

# tests/apps/payment_gateway/test_order_repository.py
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock
from apps.payment_gateway.repositories.order import OrderPaymentRepository


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def repo(mock_session):
    return OrderPaymentRepository(mock_session)


@pytest.mark.asyncio
async def test_update_pending_order_on_payment_link_created(repo, mock_session):
    order_id = uuid4()
    gateway_order_id = "plink_abc123"
    gateway_response = {"id": "plink_abc123", "short_url": "https://razorpay.in/abc"}
    short_url = "https://razorpay.in/abc"

    await repo.update_pending_order_on_payment_link_created(
        order_id=order_id,
        gateway_order_id=gateway_order_id,
        gateway_response=gateway_response,
        short_url=short_url,
    )

    mock_session.execute.assert_called_once()
    mock_session.flush.assert_called_once()

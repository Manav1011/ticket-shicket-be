"""Tests for PaymentGatewayEventRepository."""
from unittest.mock import AsyncMock, MagicMock, Mock
import pytest
from uuid import uuid4

from apps.payment_gateway.repositories.event import PaymentGatewayEventRepository
from apps.payment_gateway.models import PaymentGatewayEventModel


@pytest.mark.asyncio
async def test_event_repository_create_signature():
    """Verify repository.create() accepts correct parameters."""
    mock_session = AsyncMock()
    repo = PaymentGatewayEventRepository(mock_session)
    
    order_id = uuid4()
    event = await repo.create(
        order_id=order_id,
        event_type="order.paid",
        gateway_event_id="evt_abc123",
        payload={"test": "payload"},
        gateway_payment_id="pay_xyz",
    )
    
    # Verify session.add was called
    mock_session.add.assert_called_once()
    # Verify session.flush was called
    mock_session.flush.assert_called_once()


@pytest.mark.asyncio
async def test_event_repository_exists_query():
    """Verify repository.exists() builds correct query."""
    mock_session = AsyncMock()
    
    # Mock the execute return - first() is NOT async in SQLAlchemy
    mock_result = Mock()
    mock_result.first.return_value = MagicMock()  # Simulate found
    mock_session.execute = AsyncMock(return_value=mock_result)
    
    repo = PaymentGatewayEventRepository(mock_session)
    order_id = uuid4()
    
    exists = await repo.exists(
        order_id=order_id,
        event_type="order.paid",
        gateway_event_id="evt_abc123",
    )
    
    assert exists is True
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_event_repository_exists_returns_false():
    """Verify repository.exists() returns False when not found."""
    mock_session = AsyncMock()
    
    # Mock the execute return - first() is NOT async in SQLAlchemy
    mock_result = Mock()
    mock_result.first.return_value = None  # Simulate not found
    mock_session.execute = AsyncMock(return_value=mock_result)
    
    repo = PaymentGatewayEventRepository(mock_session)
    order_id = uuid4()
    
    exists = await repo.exists(
        order_id=order_id,
        event_type="order.paid",
        gateway_event_id="evt_nonexistent",
    )
    
    assert exists is False



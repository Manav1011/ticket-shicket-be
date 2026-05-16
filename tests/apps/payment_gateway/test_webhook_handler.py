"""Tests for RazorpayWebhookHandler."""
import pytest
from unittest.mock import AsyncMock, MagicMock, Mock
from uuid import uuid4

from apps.payment_gateway.handlers.razorpay import RazorpayWebhookHandler
from apps.payment_gateway.exceptions import WebhookVerificationError
from apps.payment_gateway.schemas.base import WebhookEvent


@pytest.mark.asyncio
async def test_handler_verifies_signature_before_processing():
    """Verify that handler verifies signature before processing."""
    mock_session = AsyncMock()
    handler = RazorpayWebhookHandler(mock_session)
    
    # Mock the gateway to return False for signature verification
    handler._gateway = MagicMock()
    handler._gateway.verify_webhook_signature.return_value = False

    with pytest.raises(WebhookVerificationError):
        await handler.handle(b"test_body", {"x-razorpay-signature": "invalid"})


@pytest.mark.asyncio
async def test_handler_routes_order_paid_event():
    """Verify that handler routes order.paid events to handle_order_paid."""
    mock_session = AsyncMock()
    handler = RazorpayWebhookHandler(mock_session)
    
    # Create mock event
    mock_event = MagicMock(spec=WebhookEvent)
    mock_event.event = "order.paid"
    
    # Mock the gateway
    handler._gateway = MagicMock()
    handler._gateway.verify_webhook_signature.return_value = True
    handler._gateway.parse_webhook_event.return_value = mock_event
    
    # Mock handle_order_paid
    handler.handle_order_paid = AsyncMock(return_value={"status": "ok"})
    
    result = await handler.handle(b"test_body", {})
    
    handler.handle_order_paid.assert_called_once_with(mock_event)
    assert result == {"status": "ok"}


@pytest.mark.asyncio
async def test_handler_routes_payment_failed_event():
    """Verify that handler routes payment.failed events."""
    mock_session = AsyncMock()
    handler = RazorpayWebhookHandler(mock_session)
    
    mock_event = MagicMock(spec=WebhookEvent)
    mock_event.event = "payment.failed"
    
    handler._gateway = MagicMock()
    handler._gateway.verify_webhook_signature.return_value = True
    handler._gateway.parse_webhook_event.return_value = mock_event
    
    handler.handle_payment_failed = AsyncMock(return_value={"status": "ok"})
    
    result = await handler.handle(b"test_body", {})
    
    handler.handle_payment_failed.assert_called_once_with(mock_event)
    assert result == {"status": "ok"}


@pytest.mark.asyncio
async def test_handler_routes_payment_link_expired():
    """Verify that handler routes payment_link.expired events."""
    mock_session = AsyncMock()
    handler = RazorpayWebhookHandler(mock_session)
    
    mock_event = MagicMock(spec=WebhookEvent)
    mock_event.event = "payment_link.expired"
    
    handler._gateway = MagicMock()
    handler._gateway.verify_webhook_signature.return_value = True
    handler._gateway.parse_webhook_event.return_value = mock_event
    
    handler.handle_payment_link_expired = AsyncMock(return_value={"status": "ok"})
    
    result = await handler.handle(b"test_body", {})
    
    handler.handle_payment_link_expired.assert_called_once_with(mock_event)
    assert result == {"status": "ok"}


@pytest.mark.asyncio
async def test_handler_routes_payment_link_cancelled():
    """Verify that handler routes payment_link.cancelled events."""
    mock_session = AsyncMock()
    handler = RazorpayWebhookHandler(mock_session)
    
    mock_event = MagicMock(spec=WebhookEvent)
    mock_event.event = "payment_link.cancelled"
    
    handler._gateway = MagicMock()
    handler._gateway.verify_webhook_signature.return_value = True
    handler._gateway.parse_webhook_event.return_value = mock_event
    
    handler.handle_payment_link_cancelled = AsyncMock(return_value={"status": "ok"})
    
    result = await handler.handle(b"test_body", {})
    
    handler.handle_payment_link_cancelled.assert_called_once_with(mock_event)
    assert result == {"status": "ok"}


@pytest.mark.asyncio
async def test_handler_ignores_unknown_events():
    """Verify that handler ignores unknown events."""
    mock_session = AsyncMock()
    handler = RazorpayWebhookHandler(mock_session)
    
    mock_event = MagicMock(spec=WebhookEvent)
    mock_event.event = "unknown.event"
    
    handler._gateway = MagicMock()
    handler._gateway.verify_webhook_signature.return_value = True
    handler._gateway.parse_webhook_event.return_value = mock_event
    
    result = await handler.handle(b"test_body", {})
    
    assert result == {"status": "ok"}

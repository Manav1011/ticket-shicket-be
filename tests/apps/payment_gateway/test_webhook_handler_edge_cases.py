"""Edge-case tests for RazorpayWebhookHandler."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from apps.payment_gateway.handlers.razorpay import RazorpayWebhookHandler
from apps.payment_gateway.schemas.base import WebhookEvent
from apps.allocation.models import OrderModel
from apps.ticketing.enums import OrderStatus


def _make_order_paid_event(order_id: str, amount: int, gateway_order_id: str = None):
    """Build a minimal order.paid WebhookEvent."""
    g_order_id = gateway_order_id or f"order_{uuid4().hex[:8]}"
    raw_payload = {
        "event": "order.paid",
        "id": f"evt_{uuid4().hex[:8]}",
        "payload": {
            "order": {
                "entity": {
                    "id": g_order_id,
                    "notes": {"internal_order_id": str(order_id)},
                }
            },
            "payment": {
                "entity": {
                    "id": f"pay_{uuid4().hex[:8]}",
                    "order_id": g_order_id,
                    "amount": amount,
                    "status": "captured",
                }
            },
        }
    }
    return WebhookEvent(
        event="order.paid",
        gateway_order_id=g_order_id,
        internal_order_id=str(order_id),
        receipt=None,
        raw_payload=raw_payload,
    )


@pytest.mark.asyncio
async def test_handle_order_paid_amount_mismatch_marks_order_failed():
    """When amount in webhook != order.final_amount, order is marked failed."""
    order_id = uuid4()
    # Webhook says 50000 paise (500 INR)
    event = _make_order_paid_event(order_id, amount=50000)

    # Order has 400.00 final_amount (40000 paise)
    order_mock = MagicMock(
        id=order_id,
        status=OrderStatus.pending,
        final_amount=400.00,
        gateway_order_id=event.gateway_order_id,
        gateway_response={},
    )
    
    mock_session = AsyncMock()
    mock_session.execute.return_value = MagicMock(
        scalar_one_or_none=MagicMock(return_value=order_mock)
    )

    handler = RazorpayWebhookHandler(mock_session)
    handler._gateway = MagicMock()
    handler._gateway.parse_webhook_event.return_value = event
    handler._gateway.verify_webhook_signature.return_value = True
    
    # Mock repos to avoid hitting DB
    handler._event_repo = AsyncMock()
    handler._ticketing_repo = AsyncMock()
    handler._gateway.cancel_payment_link = AsyncMock()

    result = await handler.handle(b"{}", {})

    assert result == {"status": "ok"}
    
    # Check that update to failed was called
    # The first execute is the SELECT, the second is the UPDATE
    assert mock_session.execute.call_count >= 2
    
    # Verify ticketing repo clear_locks was called
    handler._ticketing_repo.clear_locks_for_order.assert_called_once_with(order_id)
    # Verify gateway cancel_payment_link was called
    handler._gateway.cancel_payment_link.assert_called_once_with(event.gateway_order_id)


@pytest.mark.asyncio
async def test_handle_order_paid_idempotency_order_already_paid():
    """
    If order status is already 'paid' when webhook arrives, handler returns ok
    without attempting allocation.
    """
    order_id = uuid4()
    event = _make_order_paid_event(order_id, amount=50000)

    # Order is already paid
    order_mock = MagicMock(
        id=order_id,
        status=OrderStatus.paid,
        final_amount=500.00,
        gateway_order_id=event.gateway_order_id,
    )
    mock_session = AsyncMock()
    mock_session.execute.return_value = MagicMock(
        scalar_one_or_none=MagicMock(return_value=order_mock)
    )

    handler = RazorpayWebhookHandler(mock_session)
    handler._gateway = MagicMock()
    handler._gateway.parse_webhook_event.return_value = event
    handler._gateway.verify_webhook_signature.return_value = True
    handler._event_repo = AsyncMock()
    handler._ticketing_repo = AsyncMock()

    result = await handler.handle(b"{}", {})

    assert result == {"status": "ok"}
    # clear_locks should NOT be called for already-paid order
    handler._ticketing_repo.clear_locks_for_order.assert_not_called()


@pytest.mark.asyncio
async def test_handle_order_paid_gateway_order_id_mismatch():
    """
    When webhook's Razorpay order ID doesn't match the stored gateway_order_id,
    the handler returns ok without modification.
    """
    order_id = uuid4()
    event = _make_order_paid_event(order_id, amount=50000)

    order_mock = MagicMock(
        id=order_id,
        status=OrderStatus.pending,
        final_amount=500.00,
        gateway_order_id="razorpay_completely_different_id",
    )
    mock_session = AsyncMock()
    mock_session.execute.return_value = MagicMock(
        scalar_one_or_none=MagicMock(return_value=order_mock)
    )

    handler = RazorpayWebhookHandler(mock_session)
    handler._gateway = MagicMock()
    handler._gateway.parse_webhook_event.return_value = event
    handler._gateway.verify_webhook_signature.return_value = True
    handler._event_repo = AsyncMock()

    result = await handler.handle(b"{}", {})

    assert result == {"status": "ok"}
    # Should not have proceeded to update
    assert mock_session.execute.call_count == 1


@pytest.mark.asyncio
async def test_handle_order_paid_duplicate_event_ignored():
    """
    When a duplicate webhook event arrives (IntegrityError on event repo create),
    handler returns ok without processing (idempotency layer 4).
    """
    from sqlalchemy.exc import IntegrityError

    order_id = uuid4()
    event = _make_order_paid_event(order_id, amount=50000)

    order_mock = MagicMock(
        id=order_id,
        status=OrderStatus.pending,
        final_amount=500.00,
        gateway_order_id=event.gateway_order_id,
    )
    mock_session = AsyncMock()
    mock_session.execute.return_value = MagicMock(
        scalar_one_or_none=MagicMock(return_value=order_mock)
    )

    handler = RazorpayWebhookHandler(mock_session)
    handler._gateway = MagicMock()
    handler._gateway.parse_webhook_event.return_value = event
    handler._gateway.verify_webhook_signature.return_value = True
    
    handler._event_repo = AsyncMock()
    handler._event_repo.create = AsyncMock(side_effect=IntegrityError(None, None, None))
    handler._ticketing_repo = AsyncMock()

    result = await handler.handle(b"{}", {})

    assert result == {"status": "ok"}
    # Should not have proceeded to update order
    assert mock_session.execute.call_count == 1


@pytest.mark.asyncio
async def test_handle_payment_failed_non_pending_order():
    """
    If order status is not pending, payment.failed webhook is ignored.
    """
    g_order_id = "order_xyz"
    raw = {
        "event": "payment.failed",
        "payload": {
            "payment": {
                "entity": {
                    "order_id": g_order_id,
                    "error_description": "insufficient funds",
                }
            }
        }
    }
    event = WebhookEvent(
        event="payment.failed",
        gateway_order_id=g_order_id,
        internal_order_id=None,
        receipt=None,
        raw_payload=raw,
    )

    order_mock = MagicMock(
        id=uuid4(),
        status=OrderStatus.paid,
        gateway_order_id=g_order_id,
    )
    mock_session = AsyncMock()
    mock_session.execute.return_value = MagicMock(
        scalar_one_or_none=MagicMock(return_value=order_mock)
    )

    handler = RazorpayWebhookHandler(mock_session)
    handler._gateway = MagicMock()
    handler._gateway.parse_webhook_event.return_value = event
    handler._gateway.verify_webhook_signature.return_value = True
    handler._ticketing_repo = AsyncMock()

    result = await handler.handle(b"{}", {})

    assert result == {"status": "ok"}
    handler._ticketing_repo.clear_locks_for_order.assert_not_called()


@pytest.mark.asyncio
async def test_handle_payment_link_expired_order_not_found():
    """
    When no order matches gateway_order_id, handler returns ok.
    """
    g_order_id = "order_xyz"
    raw = {
        "event": "payment_link.expired",
        "payload": {
            "payment_link": {
                "entity": {
                    "id": "plink_abc",
                    "order_id": g_order_id,
                }
            }
        }
    }
    event = WebhookEvent(
        event="payment_link.expired",
        gateway_order_id=g_order_id,
        internal_order_id=None,
        receipt=None,
        raw_payload=raw,
    )

    mock_session = AsyncMock()
    mock_session.execute.return_value = MagicMock(
        scalar_one_or_none=MagicMock(return_value=None)
    )

    handler = RazorpayWebhookHandler(mock_session)
    handler._gateway = MagicMock()
    handler._gateway.parse_webhook_event.return_value = event
    handler._gateway.verify_webhook_signature.return_value = True
    handler._ticketing_repo = AsyncMock()

    result = await handler.handle(b"{}", {})

    assert result == {"status": "ok"}
    handler._gateway.cancel_payment_link.assert_not_called()


@pytest.mark.asyncio
async def test_handle_payment_link_cancelled_non_pending():
    """
    When order is not pending, payment_link.cancelled is ignored.
    """
    g_order_id = "order_xyz"
    raw = {
        "event": "payment_link.cancelled",
        "payload": {
            "payment_link": {
                "entity": {
                    "id": "plink_abc",
                    "order_id": g_order_id,
                }
            }
        }
    }
    event = WebhookEvent(
        event="payment_link.cancelled",
        gateway_order_id=g_order_id,
        internal_order_id=None,
        receipt=None,
        raw_payload=raw,
    )

    order_mock = MagicMock(
        id=uuid4(),
        status=OrderStatus.paid,
        gateway_order_id=g_order_id,
    )
    mock_session = AsyncMock()
    mock_session.execute.return_value = MagicMock(
        scalar_one_or_none=MagicMock(return_value=order_mock)
    )

    handler = RazorpayWebhookHandler(mock_session)
    handler._gateway = MagicMock()
    handler._gateway.parse_webhook_event.return_value = event
    handler._gateway.verify_webhook_signature.return_value = True
    handler._ticketing_repo = AsyncMock()

    result = await handler.handle(b"{}", {})

    assert result == {"status": "ok"}
    handler._ticketing_repo.clear_locks_for_order.assert_not_called()
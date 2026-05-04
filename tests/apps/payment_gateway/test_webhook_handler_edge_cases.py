"""Edge case tests for RazorpayWebhookHandler."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from apps.payment_gateway.handlers.razorpay import RazorpayWebhookHandler
from apps.payment_gateway.schemas.base import WebhookEvent
from apps.ticketing.enums import OrderStatus
from apps.allocation.models import OrderModel
from sqlalchemy.exc import IntegrityError


def _make_order_paid_event(order_id: str, amount: int, gateway_order_id: str = "razorpay_order_123") -> WebhookEvent:
    """Build a WebhookEvent for order.paid with the given order ID and amount in paisa."""
    return WebhookEvent.from_razorpay(
        event="order.paid",
        gateway_order_id=gateway_order_id,
        internal_order_id=order_id,
        receipt=None,
        raw_payload={
            "id": f"evt_{uuid4().hex[:12]}",
            "payload": {
                "order": {
                    "entity": {
                        "id": gateway_order_id,
                    }
                },
                "payment": {
                    "entity": {
                        "id": f"pay_{uuid4().hex[:12]}",
                        "order_id": gateway_order_id,
                        "amount": amount,
                        "status": "captured",
                    }
                },
            },
        },
    )


def _make_payment_failed_event(gateway_order_id: str) -> WebhookEvent:
    """Build a WebhookEvent for payment.failed."""
    return WebhookEvent.from_razorpay(
        event="payment.failed",
        gateway_order_id=gateway_order_id,
        internal_order_id=None,
        receipt=None,
        raw_payload={
            "id": f"evt_{uuid4().hex[:12]}",
            "payload": {
                "payment": {
                    "entity": {
                        "order_id": gateway_order_id,
                        "error_description": "payment_failed",
                    }
                },
            },
        },
    )


def _make_payment_link_expired_event(gateway_order_id: str) -> WebhookEvent:
    """Build a WebhookEvent for payment_link.expired."""
    return WebhookEvent.from_razorpay(
        event="payment_link.expired",
        gateway_order_id=gateway_order_id,
        internal_order_id=None,
        receipt=None,
        raw_payload={},
    )


def _make_payment_link_cancelled_event(gateway_order_id: str) -> WebhookEvent:
    """Build a WebhookEvent for payment_link.cancelled."""
    return WebhookEvent.from_razorpay(
        event="payment_link.cancelled",
        gateway_order_id=gateway_order_id,
        internal_order_id=None,
        receipt=None,
        raw_payload={},
    )


def _mock_order(status=OrderStatus.pending, final_amount=100.00, gateway_order_id="razorpay_order_123", order_id=None):
    """Create a mock OrderModel with given state."""
    order = MagicMock(spec=OrderModel)
    order.id = order_id or uuid4()
    order.status = status
    order.final_amount = final_amount
    order.gateway_order_id = gateway_order_id
    return order


# =============================================================================
# Test 1: amount mismatch -> order marked failed, locks cleared, link cancelled
# =============================================================================

@pytest.mark.asyncio
async def test_handle_order_paid_amount_mismatch_marks_order_failed():
    """
    When amount in webhook != order.final_amount*100, the order is marked
    failed, locks cleared, payment link cancelled.
    """
    order_id = uuid4()
    # order.final_amount = 100.00 -> expected 10000 paisa, but webhook has 5000
    order = _mock_order(
        status=OrderStatus.pending,
        final_amount=100.00,
        gateway_order_id="razorpay_order_123",
        order_id=order_id,
    )

    mock_session = AsyncMock()
    # Mock session.execute to return different values on successive calls:
    # 1. First call: SELECT order -> returns order
    # 2. Second call: UPDATE order to failed -> returns rowcount=1
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = order
    mock_update_result = MagicMock()
    mock_update_result.rowcount = 1
    mock_session.execute.side_effect = [mock_result, mock_update_result]

    handler = RazorpayWebhookHandler(mock_session)
    handler._gateway = MagicMock()
    handler._gateway.cancel_payment_link = AsyncMock(return_value=None)
    handler._ticketing_repo = MagicMock()
    handler._ticketing_repo.clear_locks_for_order = AsyncMock(return_value=None)
    handler._event_repo = MagicMock()
    handler._event_repo.create = AsyncMock(return_value=MagicMock())  # no IntegrityError

    event = _make_order_paid_event(
        order_id=str(order_id),
        amount=5000,  # 50.00 INR vs expected 100.00 INR = 10000 paisa
        gateway_order_id="razorpay_order_123",
    )

    result = await handler.handle_order_paid(event)

    assert result == {"status": "ok"}
    # Verify locks cleared and link cancelled
    handler._ticketing_repo.clear_locks_for_order.assert_called_once_with(order_id)
    handler._gateway.cancel_payment_link.assert_called_once_with("razorpay_order_123")


# =============================================================================
# Test 2: idempotency — already paid order returns ok without processing
# =============================================================================

@pytest.mark.asyncio
async def test_handle_order_paid_idempotency_order_already_paid():
    """
    If order status is already 'paid' when webhook arrives, handler returns
    ok without processing.
    """
    order_id = uuid4()
    order = _mock_order(
        status=OrderStatus.paid,  # already paid
        final_amount=100.00,
        gateway_order_id="razorpay_order_123",
        order_id=order_id,
    )

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = order
    mock_session.execute.return_value = mock_result

    handler = RazorpayWebhookHandler(mock_session)
    handler._gateway = MagicMock()
    handler._event_repo = MagicMock()
    # No need to mock anything else since it should short-circuit

    event = _make_order_paid_event(
        order_id=str(order_id),
        amount=10000,
        gateway_order_id="razorpay_order_123",
    )

    result = await handler.handle_order_paid(event)

    assert result == {"status": "ok"}
    # No further processing — no event repo create, no gateway calls
    handler._event_repo.create.assert_not_called()


# =============================================================================
# Test 3: gateway_order_id mismatch — handler returns ok
# =============================================================================

@pytest.mark.asyncio
async def test_handle_order_paid_gateway_order_id_mismatch():
    """
    When webhook's Razorpay order ID doesn't match stored gateway_order_id,
    handler returns ok.
    """
    order_id = uuid4()
    order = _mock_order(
        status=OrderStatus.pending,
        final_amount=100.00,
        gateway_order_id="razorpay_order_123",
        order_id=order_id,
    )

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = order
    mock_session.execute.return_value = mock_result

    handler = RazorpayWebhookHandler(mock_session)
    handler._gateway = MagicMock()
    handler._event_repo = MagicMock()
    handler._event_repo.create = AsyncMock(return_value=MagicMock())

    # Webhook has a DIFFERENT gateway order ID
    event = _make_order_paid_event(
        order_id=str(order_id),
        amount=10000,
        gateway_order_id="razorpay_order_WRONG",  # mismatch
    )

    result = await handler.handle_order_paid(event)

    assert result == {"status": "ok"}
    # gateway_order_id mismatch is logged but returns ok


# =============================================================================
# Test 4: duplicate event — IntegrityError on event repo create returns ok
# =============================================================================

@pytest.mark.asyncio
async def test_handle_order_paid_duplicate_event_ignored():
    """
    When IntegrityError raised on event repo create (unique constraint
    violation), handler returns ok (idempotency layer 4).
    """
    order_id = uuid4()
    order = _mock_order(
        status=OrderStatus.pending,
        final_amount=100.00,
        gateway_order_id="razorpay_order_123",
        order_id=order_id,
    )

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = order
    mock_session.execute.return_value = mock_result

    handler = RazorpayWebhookHandler(mock_session)
    handler._gateway = MagicMock()
    handler._ticketing_repo = MagicMock()
    handler._ticketing_repo.clear_locks_for_order = AsyncMock(return_value=None)
    # IntegrityError simulates unique constraint violation on duplicate event
    handler._event_repo = MagicMock()
    handler._event_repo.create = AsyncMock(side_effect=IntegrityError(None, None, None))

    event = _make_order_paid_event(
        order_id=str(order_id),
        amount=10000,
        gateway_order_id="razorpay_order_123",
    )

    result = await handler.handle_order_paid(event)

    assert result == {"status": "ok"}
    # Should have caught IntegrityError and returned ok


# =============================================================================
# Test 5: payment.failed on non-pending order — ignored
# =============================================================================

@pytest.mark.asyncio
async def test_handle_payment_failed_non_pending_order():
    """
    If order status != pending, payment.failed is ignored.
    """
    order_id = uuid4()
    order = _mock_order(
        status=OrderStatus.paid,  # not pending
        final_amount=100.00,
        gateway_order_id="razorpay_order_123",
        order_id=order_id,
    )

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = order
    mock_session.execute.return_value = mock_result

    handler = RazorpayWebhookHandler(mock_session)
    handler._ticketing_repo = MagicMock()
    handler._ticketing_repo.clear_locks_for_order = AsyncMock(return_value=None)

    event = _make_payment_failed_event(gateway_order_id="razorpay_order_123")

    result = await handler.handle_payment_failed(event)

    assert result == {"status": "ok"}
    handler._ticketing_repo.clear_locks_for_order.assert_not_called()


# =============================================================================
# Test 6: payment_link.expired — order not found returns ok
# =============================================================================

@pytest.mark.asyncio
async def test_handle_payment_link_expired_order_not_found():
    """
    When no order matches gateway_order_id, handler returns ok.
    """
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None  # no order found
    mock_session.execute.return_value = mock_result

    handler = RazorpayWebhookHandler(mock_session)
    handler._gateway = MagicMock()
    handler._gateway.cancel_payment_link = AsyncMock(return_value=None)
    handler._ticketing_repo = MagicMock()
    handler._ticketing_repo.clear_locks_for_order = AsyncMock(return_value=None)

    event = _make_payment_link_expired_event(gateway_order_id="nonexistent_order")

    result = await handler.handle_payment_link_expired(event)

    assert result == {"status": "ok"}
    handler._gateway.cancel_payment_link.assert_not_called()


# =============================================================================
# Test 7: payment_link.cancelled on non-pending order — ignored
# =============================================================================

@pytest.mark.asyncio
async def test_handle_payment_link_cancelled_non_pending():
    """
    When order is not pending, payment_link.cancelled is ignored.
    """
    order_id = uuid4()
    order = _mock_order(
        status=OrderStatus.failed,  # not pending
        final_amount=100.00,
        gateway_order_id="razorpay_order_123",
        order_id=order_id,
    )

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = order
    mock_session.execute.return_value = mock_result

    handler = RazorpayWebhookHandler(mock_session)
    handler._ticketing_repo = MagicMock()
    handler._ticketing_repo.clear_locks_for_order = AsyncMock(return_value=None)

    event = _make_payment_link_cancelled_event(gateway_order_id="razorpay_order_123")

    result = await handler.handle_payment_link_cancelled(event)

    assert result == {"status": "ok"}
    handler._ticketing_repo.clear_locks_for_order.assert_not_called()
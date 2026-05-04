import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from apps.payment_gateway.services.razorpay import RazorpayPaymentGateway
from apps.payment_gateway.services.base import BuyerInfo, PaymentLinkResult
from uuid import uuid4


@patch('apps.payment_gateway.services.razorpay.get_razorpay_client')
@pytest.mark.asyncio
async def test_create_payment_link_returns_correct_result(mock_get_client):
    mock_client = MagicMock()
    mock_client.payment_link.create.return_value = {
        "id": "plink_abc123",
        "short_url": "https://razorpay.in/pl/abc123",
        "amount": 100000,
        "currency": "INR",
        "status": "created",
    }
    mock_get_client.return_value = mock_client

    gateway = RazorpayPaymentGateway()
    order_id = uuid4()
    event_id = uuid4()
    buyer_holder_id = uuid4()

    result = await gateway.create_payment_link(
        order_id=order_id,
        amount=100000,
        currency="INR",
        buyer=BuyerInfo(name="John", email="john@test.com", phone="+919999999999"),
        description="Test transfer",
        event_id=event_id,
        flow_type="b2b_transfer",
        transfer_type="organizer_to_reseller",
        buyer_holder_id=buyer_holder_id,
    )

    assert isinstance(result, PaymentLinkResult)
    assert result.gateway_order_id == "plink_abc123"
    assert result.short_url == "https://razorpay.in/pl/abc123"
    assert "id" in result.gateway_response


@patch('apps.payment_gateway.services.razorpay.get_razorpay_client')
@pytest.mark.asyncio
async def test_create_payment_link_calls_with_correct_notes(mock_get_client):
    mock_client = MagicMock()
    mock_client.payment_link.create.return_value = {
        "id": "plink_abc123",
        "short_url": "https://razorpay.in/pl/abc123",
    }
    mock_get_client.return_value = mock_client

    gateway = RazorpayPaymentGateway()
    order_id = uuid4()
    event_id = uuid4()
    buyer_holder_id = uuid4()

    await gateway.create_payment_link(
        order_id=order_id,
        amount=100000,
        currency="INR",
        buyer=BuyerInfo(name="John", email="john@test.com", phone="+919999999999"),
        description="Test transfer",
        event_id=event_id,
        flow_type="b2b_transfer",
        transfer_type="organizer_to_reseller",
        buyer_holder_id=buyer_holder_id,
    )

    call_kwargs = mock_client.payment_link.create.call_args.kwargs
    payload = call_kwargs["data"]
    assert payload["amount"] == 100000
    assert payload["currency"] == "INR"
    assert payload["description"] == "Test transfer"
    assert payload["notify"]["sms"] is False
    assert payload["notify"]["email"] is False
    notes = payload["notes"]
    assert notes["internal_order_id"] == str(order_id)
    assert notes["event_id"] == str(event_id)
    assert notes["flow_type"] == "b2b_transfer"
    assert notes["transfer_type"] == "organizer_to_reseller"

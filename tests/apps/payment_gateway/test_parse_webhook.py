import pytest
from unittest.mock import patch, MagicMock
from apps.payment_gateway.services.razorpay import RazorpayPaymentGateway
from apps.payment_gateway.schemas.base import WebhookEvent
import json


ORDER_PAID_PAYLOAD = {
    "event": "order.paid",
    "id": "evt_abc",
    "payload": {
        "order": {
            "entity": {
                "id": "order_xyz",
                "notes": {"internal_order_id": "uuid-123"}
            }
        },
        "payment": {
            "entity": {
                "id": "pay_123",
                "order_id": "order_xyz",
                "amount": 100000,
                "currency": "INR",
                "status": "captured",
            }
        },
    }
}

ORDER_PAID_BODY = json.dumps(ORDER_PAID_PAYLOAD).encode()

PAYMENT_LINK_EXPIRED_PAYLOAD = {
    "event": "payment_link.expired",
    "id": "evt_plink",
    "payload": {
        "payment_link": {
            "entity": {
                "id": "plink_abc",
                "order_id": "order_xyz",
                "status": "expired"
            }
        }
    }
}

PAYMENT_LINK_EXPIRED_BODY = json.dumps(PAYMENT_LINK_EXPIRED_PAYLOAD).encode()


@patch('apps.payment_gateway.services.razorpay.get_razorpay_client')
def test_parse_order_paid_extracts_internal_order_id(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    with patch('apps.payment_gateway.services.razorpay.settings') as mock_settings:
        mock_settings.RAZORPAY_WEBHOOK_SECRET = "secret"
        
        gateway = RazorpayPaymentGateway()
        event = gateway.parse_webhook_event(ORDER_PAID_BODY, {})

        assert isinstance(event, WebhookEvent)
        assert event.event == "order.paid"
        assert event.gateway_order_id == "order_xyz"
        assert event.internal_order_id == "uuid-123"
        assert event.receipt is None


@patch('apps.payment_gateway.services.razorpay.get_razorpay_client')
def test_parse_payment_link_expired(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    with patch('apps.payment_gateway.services.razorpay.settings') as mock_settings:
        mock_settings.RAZORPAY_WEBHOOK_SECRET = "secret"
        
        gateway = RazorpayPaymentGateway()
        event = gateway.parse_webhook_event(PAYMENT_LINK_EXPIRED_BODY, {})

        assert isinstance(event, WebhookEvent)
        assert event.event == "payment_link.expired"
        assert event.gateway_order_id == "plink_abc"
        assert event.internal_order_id is None

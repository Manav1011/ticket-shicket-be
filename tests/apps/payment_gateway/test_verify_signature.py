import pytest
import hmac
import hashlib
from unittest.mock import patch, MagicMock
from apps.payment_gateway.services.razorpay import RazorpayPaymentGateway
from apps.payment_gateway.exceptions import WebhookVerificationError


WEBHOOK_SECRET = "razorpay_webhook_secret_123"
VALID_BODY = b'{"event": "order.paid", "id": "evt_abc"}'


def _compute_signature(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@patch('apps.payment_gateway.services.razorpay.get_razorpay_client')
def test_verify_webhook_signature_valid(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    with patch('apps.payment_gateway.services.razorpay.settings') as mock_settings:
        mock_settings.RAZORPAY_WEBHOOK_SECRET = WEBHOOK_SECRET
        
        gateway = RazorpayPaymentGateway()

        sig = _compute_signature(VALID_BODY, WEBHOOK_SECRET)
        headers = {"x-razorpay-signature": sig}

        result = gateway.verify_webhook_signature(VALID_BODY, headers)
        assert result is True


@patch('apps.payment_gateway.services.razorpay.get_razorpay_client')
def test_verify_webhook_signature_invalid(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    with patch('apps.payment_gateway.services.razorpay.settings') as mock_settings:
        mock_settings.RAZORPAY_WEBHOOK_SECRET = WEBHOOK_SECRET
        
        gateway = RazorpayPaymentGateway()

        headers = {"x-razorpay-signature": "invalid_signature"}
        result = gateway.verify_webhook_signature(VALID_BODY, headers)
        assert result is False


@patch('apps.payment_gateway.services.razorpay.get_razorpay_client')
def test_verify_webhook_signature_missing_header(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    with patch('apps.payment_gateway.services.razorpay.settings') as mock_settings:
        mock_settings.RAZORPAY_WEBHOOK_SECRET = WEBHOOK_SECRET
        
        gateway = RazorpayPaymentGateway()

        result = gateway.verify_webhook_signature(VALID_BODY, {})
        assert result is False

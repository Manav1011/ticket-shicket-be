import pytest
from unittest.mock import patch, MagicMock
from apps.payment_gateway.services.razorpay import RazorpayPaymentGateway


@patch('apps.payment_gateway.services.razorpay.get_razorpay_client')
@pytest.mark.asyncio
async def test_cancel_payment_link_success(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    with patch('apps.payment_gateway.services.razorpay.settings') as mock_settings:
        mock_settings.RAZORPAY_WEBHOOK_SECRET = "secret"
        
        gateway = RazorpayPaymentGateway()
        result = await gateway.cancel_payment_link("plink_abc123")

        assert result is True
        mock_client.payment_link.cancel.assert_called_once_with("plink_abc123")


@patch('apps.payment_gateway.services.razorpay.get_razorpay_client')
@pytest.mark.asyncio
async def test_cancel_payment_link_already_cancelled_returns_false(mock_get_client):
    import razorpay
    mock_client = MagicMock()
    mock_client.payment_link.cancel.side_effect = razorpay.errors.BadRequestError("Link already cancelled")
    mock_get_client.return_value = mock_client

    with patch('apps.payment_gateway.services.razorpay.settings') as mock_settings:
        mock_settings.RAZORPAY_WEBHOOK_SECRET = "secret"
        
        gateway = RazorpayPaymentGateway()
        result = await gateway.cancel_payment_link("plink_abc123")

        assert result is False

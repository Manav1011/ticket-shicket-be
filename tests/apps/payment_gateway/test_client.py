import pytest
from unittest.mock import patch, MagicMock
from apps.payment_gateway.client import get_razorpay_client, RazorpayClient


def test_get_razorpay_client_returns_singleton():
    client1 = get_razorpay_client()
    client2 = get_razorpay_client()
    assert client1 is client2


@patch('apps.payment_gateway.client.settings')
def test_razorpay_client_has_payment_link_attribute(mock_settings):
    mock_settings.RAZORPAY_KEY_ID = "test_key_id"
    mock_settings.RAZORPAY_KEY_SECRET = "test_key_secret"
    
    # Reset singleton to force re-initialization with mocked settings
    RazorpayClient._instance = None
    RazorpayClient._client = None
    
    client = get_razorpay_client()
    assert hasattr(client, "payment_link")


@patch('apps.payment_gateway.client.settings')
def test_razorpay_client_has_order_attribute(mock_settings):
    mock_settings.RAZORPAY_KEY_ID = "test_key_id"
    mock_settings.RAZORPAY_KEY_SECRET = "test_key_secret"
    
    # Reset singleton to force re-initialization with mocked settings
    RazorpayClient._instance = None
    RazorpayClient._client = None
    
    client = get_razorpay_client()
    assert hasattr(client, "order")

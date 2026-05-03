import pytest
from apps.payment_gateway.services.factory import get_gateway
from apps.payment_gateway.services.razorpay import RazorpayPaymentGateway


def test_get_gateway_razorpay_returns_razorpay_gateway():
    gateway = get_gateway("razorpay")
    assert isinstance(gateway, RazorpayPaymentGateway)


def test_get_gateway_unknown_raises():
    with pytest.raises(ValueError, match="Unknown payment gateway"):
        get_gateway("unknown")

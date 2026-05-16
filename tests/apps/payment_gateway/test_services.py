import pytest
from apps.payment_gateway.services.base import PaymentGateway, BuyerInfo, PaymentLinkResult


def test_buyer_info_dataclass():
    buyer = BuyerInfo(name="John", email="john@example.com", phone="+919999999999")
    assert buyer.name == "John"
    assert buyer.email == "john@example.com"
    assert buyer.phone == "+919999999999"


def test_payment_link_result_dataclass():
    result = PaymentLinkResult(
        gateway_order_id="plink_abc123",
        short_url="https://razorpay.in/pl/abc123",
        gateway_response={"id": "plink_abc123"},
    )
    assert result.gateway_order_id == "plink_abc123"
    assert result.short_url == "https://razorpay.in/pl/abc123"


def test_payment_gateway_is_abc():
    with pytest.raises(TypeError):
        PaymentGateway()  # Cannot instantiate ABC

"""Factory for getting payment gateway instances."""
from apps.payment_gateway.services.razorpay import RazorpayPaymentGateway
from apps.payment_gateway.services.base import PaymentGateway


def get_gateway(gateway_name: str) -> PaymentGateway:
    """Return the payment gateway instance for the given name."""
    if gateway_name == "razorpay":
        return RazorpayPaymentGateway()
    raise ValueError(f"Unknown payment gateway: {gateway_name}")

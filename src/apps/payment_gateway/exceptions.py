"""Payment gateway exceptions."""


class PaymentGatewayError(Exception):
    """Base exception for all payment gateway errors."""


class WebhookVerificationError(PaymentGatewayError):
    """Raised when webhook signature verification fails."""

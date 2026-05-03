"""RazorpayPaymentGateway implementation — stub for Phase 1.

Phase 2 implements create_payment_link, verify_webhook_signature,
parse_webhook_event, and cancel_payment_link.
"""
import razorpay

from apps.payment_gateway.client import get_razorpay_client
from apps.payment_gateway.services.base import (
    BuyerInfo,
    CheckoutOrderResult,
    PaymentGateway,
    PaymentLinkResult,
)
from apps.payment_gateway.schemas.base import WebhookEvent


class RazorpayPaymentGateway(PaymentGateway):
    def __init__(self):
        self._client = get_razorpay_client()
        self._webhook_secret = None  # Set via settings in Phase 2

    async def create_payment_link(
        self,
        order_id,
        amount: int,
        currency: str,
        buyer: BuyerInfo,
        description: str,
        event_id,
        flow_type: str,
        transfer_type: str | None,
        buyer_holder_id,
    ) -> PaymentLinkResult:
        raise NotImplementedError("Phase 2 — coming next")

    async def create_checkout_order(self, order_id, amount: int, currency: str, event_id) -> CheckoutOrderResult:
        raise NotImplementedError("Phase 2 — online checkout not implemented in V1")

    def verify_webhook_signature(self, body: bytes, headers: dict) -> bool:
        raise NotImplementedError("Phase 2 — coming next")

    def parse_webhook_event(self, body: bytes, headers: dict) -> WebhookEvent:
        raise NotImplementedError("Phase 2 — coming next")

    async def cancel_payment_link(self, payment_link_id: str) -> bool:
        raise NotImplementedError("Phase 2 — coming next")

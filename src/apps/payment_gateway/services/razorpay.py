"""RazorpayPaymentGateway implementation."""
import razorpay
import json
import hmac
import hashlib
import logging
from config import settings

from apps.payment_gateway.client import get_razorpay_client
from apps.payment_gateway.services.base import (
    BuyerInfo,
    CheckoutOrderResult,
    PaymentGateway,
    PaymentLinkResult,
)
from apps.payment_gateway.schemas.base import WebhookEvent

logger = logging.getLogger(__name__)


class RazorpayPaymentGateway(PaymentGateway):
    def __init__(self):
        self._client = get_razorpay_client()
        self._webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET

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
        payload = {
            "amount": amount,
            "currency": currency,
            "description": description,
            "customer": {
                "name": buyer.name,
                "email": buyer.email,
                "contact": buyer.phone,
            },
            "notes": {
                "internal_order_id": str(order_id),
                "event_id": str(event_id),
                "flow_type": flow_type,
                "transfer_type": transfer_type,
            },
            "notify": {
                "sms": False,
                "email": False,
            },
        }

        response = self._client.payment_link.create(payload=payload)
        gateway_order_id = response.get("id")
        short_url = response.get("short_url")

        return PaymentLinkResult(
            gateway_order_id=gateway_order_id,
            short_url=short_url,
            gateway_response=response,
        )

    async def create_checkout_order(self, order_id, amount: int, currency: str, event_id) -> CheckoutOrderResult:
        raise NotImplementedError("Phase 2 — online checkout not implemented in V1")

    def verify_webhook_signature(self, body: bytes, headers: dict) -> bool:
        received_sig = headers.get("x-razorpay-signature")
        if not received_sig:
            return False
        expected_sig = hmac.new(
            self._webhook_secret.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected_sig, received_sig)

    def parse_webhook_event(self, body: bytes, headers: dict) -> WebhookEvent:
        raw = json.loads(body)
        event_type = raw.get("event")

        if event_type == "order.paid":
            from apps.payment_gateway.schemas.razorpay import OrderPaidPayload
            parsed = OrderPaidPayload.model_validate(raw)
            order_entity = parsed.payload.order.entity
            gateway_order_id = order_entity.id
            notes = order_entity.notes or {}
            internal_order_id = notes.get("internal_order_id")
            receipt = order_entity.receipt

        elif event_type in ("payment_link.expired", "payment_link.cancelled"):
            from apps.payment_gateway.schemas.razorpay import PaymentLinkPayload
            parsed = PaymentLinkPayload.model_validate(raw)
            gateway_order_id = parsed.payload.payment_link.entity.id
            internal_order_id = None
            receipt = None

        elif event_type == "payment.failed":
            from apps.payment_gateway.schemas.razorpay import PaymentFailedPayload
            parsed = PaymentFailedPayload.model_validate(raw)
            gateway_order_id = parsed.payload.payment.entity.order_id
            internal_order_id = None
            receipt = None

        else:
            raise ValueError(f"Unknown Razorpay webhook event: {event_type}")

        return WebhookEvent(
            event=event_type,
            gateway_order_id=gateway_order_id,
            internal_order_id=internal_order_id,
            receipt=receipt,
            raw_payload=raw,
        )

    async def cancel_payment_link(self, payment_link_id: str) -> bool:
        raise NotImplementedError("Phase 2 — coming next")

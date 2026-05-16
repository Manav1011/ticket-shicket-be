"""Base webhook schemas and dataclasses."""
from dataclasses import dataclass
from typing import Any


@dataclass
class WebhookEvent:
    event: str
    gateway_order_id: str
    internal_order_id: str | None
    receipt: str | None
    raw_payload: dict

    @classmethod
    def from_razorpay(cls, event: str, gateway_order_id: str, internal_order_id: str | None, receipt: str | None, raw_payload: dict) -> "WebhookEvent":
        return cls(
            event=event,
            gateway_order_id=gateway_order_id,
            internal_order_id=internal_order_id,
            receipt=receipt,
            raw_payload=raw_payload,
        )

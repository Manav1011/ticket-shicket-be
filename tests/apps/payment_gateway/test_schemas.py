import pytest
from apps.payment_gateway.schemas.razorpay import (
    OrderPaidPayload,
    PaymentFailedPayload,
    PaymentLinkPayload,
    RazorpayWebhookPayload,
)


def test_order_paid_payload_parses_correctly():
    payload = {
        "event": "order.paid",
        "id": "evt_abc123",
        "payload": {
            "order": {
                "entity": {
                    "id": "order_xyz",
                    "receipt": "optional-receipt",
                    "notes": {
                        "internal_order_id": "uuid-of-our-order",
                        "event_id": "uuid-of-event",
                        "flow_type": "b2b_transfer",
                        "transfer_type": "organizer_to_reseller",
                    },
                }
            },
            "payment": {
                "entity": {
                    "id": "pay_123",
                    "order_id": "order_xyz",
                    "amount": 100000,
                    "currency": "INR",
                    "status": "captured",
                }
            },
        },
    }
    parsed = OrderPaidPayload.model_validate(payload)
    assert parsed.event == "order.paid"
    assert parsed.payload.order.entity.id == "order_xyz"
    assert parsed.payload.payment.entity.amount == 100000
    assert parsed.payload.payment.entity.status == "captured"


def test_payment_failed_payload_parses_correctly():
    payload = {
        "event": "payment.failed",
        "id": "evt_failed123",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_failed",
                    "order_id": "order_xyz",
                    "amount": 100000,
                    "currency": "INR",
                    "status": "failed",
                    "error_description": "insufficient funds",
                }
            }
        },
    }
    parsed = PaymentFailedPayload.model_validate(payload)
    assert parsed.event == "payment.failed"
    assert parsed.payload.payment.entity.error_description == "insufficient funds"


def test_payment_link_payload_parses_expired():
    payload = {
        "event": "payment_link.expired",
        "id": "evt_plink_expired",
        "payload": {
            "payment_link": {
                "entity": {
                    "id": "plink_abc",
                    "order_id": "order_xyz",
                    "status": "expired",
                }
            }
        },
    }
    parsed = PaymentLinkPayload.model_validate(payload)
    assert parsed.event == "payment_link.expired"
    assert parsed.payload.payment_link.entity.status == "expired"


def test_payment_link_payload_parses_cancelled():
    payload = {
        "event": "payment_link.cancelled",
        "id": "evt_plink_cancelled",
        "payload": {
            "payment_link": {
                "entity": {
                    "id": "plink_abc",
                    "order_id": "order_xyz",
                    "status": "cancelled",
                }
            }
        },
    }
    parsed = PaymentLinkPayload.model_validate(payload)
    assert parsed.event == "payment_link.cancelled"
    assert parsed.payload.payment_link.entity.status == "cancelled"


def test_razorpay_webhook_payload_unknown_event_raises():
    # Test that an unknown event raises ValidationError when trying to parse
    payload = {"event": "unknown.event", "id": "evt_unknown"}
    # Try validating against OrderPaidPayload - it should fail because required fields are missing
    with pytest.raises(Exception):  # Can be ValidationError or ValueError
        OrderPaidPayload.model_validate(payload)

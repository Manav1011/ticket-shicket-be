"""Razorpay Pydantic schemas for all webhook events."""
from pydantic import BaseModel, Field
from typing import Union


class OrderNotes(BaseModel):
    internal_order_id: str | None = None
    event_id: str | None = None
    flow_type: str | None = None
    transfer_type: str | None = None


class OrderEntity(BaseModel):
    id: str
    receipt: str | None = None
    notes: dict | None = None


class PaymentEntity(BaseModel):
    id: str
    order_id: str
    amount: int
    currency: str
    status: str
    error_description: str | None = None


class OrderPayload(BaseModel):
    entity: OrderEntity


class PaymentPayload(BaseModel):
    entity: PaymentEntity


class PaymentLinkEntity(BaseModel):
    id: str
    order_id: str | None = None
    status: str


class PaymentLinkEntityWrapper(BaseModel):
    entity: PaymentLinkEntity


class PaymentLinkPayloadWrapper(BaseModel):
    payment_link: PaymentLinkEntityWrapper


class OrderPaidOrderPayload(BaseModel):
    order: OrderPayload
    payment: PaymentPayload


class OrderFailedPaymentPayload(BaseModel):
    payment: PaymentPayload


class OrderPaidPayload(BaseModel):
    event: str
    id: str | None = None
    payload: OrderPaidOrderPayload


class PaymentFailedPayload(BaseModel):
    event: str
    id: str | None = None
    payload: OrderFailedPaymentPayload


class PaymentLinkPayload(BaseModel):
    event: str
    id: str | None = None
    payload: PaymentLinkPayloadWrapper


# Union type for all webhook events
RazorpayWebhookPayload = Union[OrderPaidPayload, PaymentFailedPayload, PaymentLinkPayload]



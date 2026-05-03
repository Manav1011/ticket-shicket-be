"""PaymentGateway ABC interface."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID


@dataclass
class BuyerInfo:
    name: str
    email: str | None
    phone: str


@dataclass
class PaymentLinkResult:
    gateway_order_id: str
    short_url: str
    gateway_response: dict


@dataclass
class CheckoutOrderResult:
    gateway_order_id: str
    amount: int
    currency: str
    key_id: str
    gateway_response: dict


class PaymentGateway(ABC):
    @abstractmethod
    async def create_payment_link(
        self,
        order_id: UUID,
        amount: int,
        currency: str,
        buyer: BuyerInfo,
        description: str,
        event_id: UUID,
        flow_type: str,
        transfer_type: str | None,
        buyer_holder_id: UUID,
    ) -> PaymentLinkResult:
        ...

    @abstractmethod
    async def create_checkout_order(
        self,
        order_id: UUID,
        amount: int,
        currency: str,
        event_id: UUID,
    ) -> CheckoutOrderResult:
        ...

    @abstractmethod
    def verify_webhook_signature(self, body: bytes, headers: dict) -> bool:
        ...

    @abstractmethod
    def parse_webhook_event(self, body: bytes, headers: dict) -> "WebhookEvent":
        ...

    @abstractmethod
    async def cancel_payment_link(self, payment_link_id: str) -> bool:
        ...

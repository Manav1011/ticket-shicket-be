"""PaymentGatewayEventRepository for managing payment gateway events."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.payment_gateway.models import PaymentGatewayEventModel


class PaymentGatewayEventRepository:
    """Repository for payment gateway audit log events."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        order_id: UUID,
        event_type: str,
        gateway_event_id: str | None,
        payload: dict,
        gateway_payment_id: str | None,
    ) -> PaymentGatewayEventModel:
        """
        Insert a gateway event. Unique constraint on (order_id, event_type, gateway_event_id)
        handles deduplication.
        """
        event = PaymentGatewayEventModel(
            order_id=order_id,
            event_type=event_type,
            gateway_event_id=gateway_event_id,
            payload=payload,
            gateway_payment_id=gateway_payment_id,
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def exists(
        self,
        order_id: UUID,
        event_type: str,
        gateway_event_id: str,
    ) -> bool:
        """Check if an event already exists (for pre-check before insert)."""
        result = await self.session.execute(
            select(PaymentGatewayEventModel).where(
                PaymentGatewayEventModel.order_id == order_id,
                PaymentGatewayEventModel.event_type == event_type,
                PaymentGatewayEventModel.gateway_event_id == gateway_event_id,
            )
        )
        return result.first() is not None

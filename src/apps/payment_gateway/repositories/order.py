"""OrderPaymentRepository — update payment fields on OrderModel."""
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from apps.allocation.models import OrderModel


class OrderPaymentRepository:
    """Updates payment gateway fields on OrderModel."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def update_pending_order_on_payment_link_created(
        self,
        order_id: UUID,
        gateway_order_id: str,
        gateway_response: dict,
        short_url: str,
    ) -> None:
        """
        Update order with Razorpay payment link details after link is created.
        Sets gateway_order_id, gateway_response, short_url.
        Called when a paid transfer flow creates a payment link.
        """
        await self._session.execute(
            update(OrderModel)
            .where(OrderModel.id == order_id)
            .values(
                gateway_order_id=gateway_order_id,
                gateway_response=gateway_response,
                short_url=short_url,
            )
        )
        await self._session.flush()

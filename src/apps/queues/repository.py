from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from apps.ticketing.enums import OrderStatus
from apps.allocation.models import OrderModel
from apps.ticketing.models import TicketModel


class OrderExpiryRepository:
    """
    Repository for order expiry operations.
    Used by the scheduler-based expiry worker (ExpiryWorker).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

    async def bulk_expire_pending_orders(self) -> list[dict]:
        """
        Bulk expire all pending orders past their lock_expires_at.

        Returns:
            List of dicts: [{"id": UUID, "gateway_type": str, "gateway_order_id": str}, ...]
        """
        stmt = (
            update(OrderModel)
            .where(
                OrderModel.status == OrderStatus.pending,
                OrderModel.lock_expires_at.is_not(None),
                OrderModel.lock_expires_at < datetime.utcnow(),
            )
            .values(
                status=OrderStatus.expired,
                expired_at=datetime.utcnow(),
            )
            .returning(OrderModel.id, OrderModel.gateway_type, OrderModel.gateway_order_id)
        )
        result = await self._session.execute(stmt)
        rows = result.fetchall()
        return [
            {
                "id": row.id,
                "gateway_type": row.gateway_type,
                "gateway_order_id": row.gateway_order_id,
            }
            for row in rows
        ]

    async def clear_ticket_locks(self, order_id: UUID) -> int:
        """
        Clear all ticket locks for an expired order.
        Returns number of tickets unlocked.
        """
        stmt = (
            update(TicketModel)
            .where(
                TicketModel.lock_reference_id == order_id,
                TicketModel.lock_reference_type == "order",
            )
            .values(
                lock_reference_type=None,
                lock_reference_id=None,
                lock_expires_at=None,
            )
        )
        result = await self._session.execute(stmt)
        return result.rowcount

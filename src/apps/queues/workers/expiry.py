import asyncio
import logging

from apps.allocation.enums import GatewayType
from apps.ticketing.enums import OrderStatus
from db.session import async_session
from apps.queues.repository import OrderExpiryRepository


logger = logging.getLogger(__name__)

# Interval between expiry scans
EXPIRY_SCAN_INTERVAL = 30  # seconds


class ExpiryWorker:
    """
    Scheduler-based expiry worker that runs every 30 seconds.

    Flow:
      1. Repository.bulk_expire_pending_orders() — single UPDATE with RETURNING
      2. For each expired order: clear locks via repository, cancel payment link (fire-and-forget)
      3. Log results

    NOT message-driven — runs on a timer and uses SQLAlchemy repositories.
    """

    def __init__(self):
        self._running = False

    async def start(self):
        self._running = True
        logger.info("Expiry worker started (interval=30s)")

        while self._running:
            try:
                await self._run_expiry_scan()
            except Exception as e:
                logger.error(f"Expiry scan error: {e}")
            await asyncio.sleep(EXPIRY_SCAN_INTERVAL)

    async def stop(self):
        self._running = False
        logger.info("Expiry worker stopped")

    async def _run_expiry_scan(self):
        """Bulk expire all pending orders past their lock time."""
        async with async_session() as session:
            repo = OrderExpiryRepository(session)
            expired_orders = await repo.bulk_expire_pending_orders()
            await session.commit()

        if not expired_orders:
            logger.debug("No orders to expire")
            return

        logger.info(f"Bulk expired {len(expired_orders)} orders")

        for order in expired_orders:
            asyncio.create_task(self._handle_expired_order(order))

    async def _handle_expired_order(self, order: dict):
        """Clear locks and cancel payment link for one expired order."""
        async with async_session() as session:
            repo = OrderExpiryRepository(session)
            unlocked = await repo.clear_ticket_locks(order["id"])
            await session.commit()
            logger.debug(f"Unlocked {unlocked} tickets for order {order['id']}")

        # Cancel Razorpay payment link (fire and forget, retry with backoff)
        if order["gateway_type"] == GatewayType.RAZORPAY_PAYMENT_LINK.value:
            if order["gateway_order_id"]:
                asyncio.create_task(
                    self._cancel_payment_link(order["gateway_order_id"])
                )

        logger.info(f"Expired order {order['id']} processed")

    async def _cancel_payment_link(self, gateway_order_id: str):
        """Cancel Razorpay payment link — fire and forget."""
        if not gateway_order_id:
            return
        try:
            from apps.payment_gateway.services.factory import get_gateway

            gateway = get_gateway("razorpay")
            await gateway.cancel_payment_link(gateway_order_id)
            logger.info(f"Payment link cancelled: {gateway_order_id}")
        except Exception as e:
            logger.error(f"Failed to cancel payment link {gateway_order_id}: {e}")


async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    worker = ExpiryWorker()
    await worker.start()


if __name__ == "__main__":
    asyncio.run(main())

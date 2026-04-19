"""
APScheduler job: cleans up tickets with expired lock_reference_id.
Runs every 5 minutes, in batches of 1000 to avoid locking the table.
Tickets locked for transfer requests that died mid-flight get unlocked here.
"""
from sqlalchemy import select, update, func

from apps.ticketing.models import TicketModel
from utils.scheduler import scheduler
from utils import logger

BATCH_SIZE = 1000


@scheduler.scheduled_job("interval", minutes=5, id="cleanup_expired_ticket_locks")
async def cleanup_expired_ticket_locks():
    """
    Every 5 minutes: find tickets with expired lock_expires_at and clear their lock.
    Processes in batches of 1000 to avoid heavy table locks.
    Tickets without lock_expires_at set are never touched.
    """
    from db.session import db_session

    async with db_session() as session:
        total_cleaned = 0
        while True:
            # Select up to BATCH_SIZE expired ticket IDs
            result = await session.execute(
                select(TicketModel.id)
                .where(
                    TicketModel.lock_expires_at < func.now(),
                    TicketModel.lock_reference_id.isnot(None),
                )
                .limit(BATCH_SIZE)
            )
            rows = result.all()
            if not rows:
                break

            ticket_ids = [r[0] for r in rows]

            # Clear lock fields in one UPDATE per batch
            await session.execute(
                update(TicketModel)
                .where(TicketModel.id.in_(ticket_ids))
                .values(
                    lock_reference_type=None,
                    lock_reference_id=None,
                    lock_expires_at=None,
                )
            )
            await session.commit()

            total_cleaned += len(ticket_ids)
            logger.warning(
                f"Cleaned up batch of {len(ticket_ids)} expired transfer locks (total: {total_cleaned})"
            )

            # If we got fewer than BATCH_SIZE, we're done for this run
            if len(ticket_ids) < BATCH_SIZE:
                break

"""
Background workers for B2B request lifecycle.
"""
import logging
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select, update

from apps.superadmin.models import B2BRequestModel
from apps.superadmin.enums import B2BRequestStatus

logger = logging.getLogger(__name__)


class B2BExpiryWorker:
    """
    Safety-net worker to expire stale approved_paid B2B requests
    when Razorpay fails to fire the payment_link.expired webhook.

    Should be scheduled to run every hour.
    """

    def __init__(self, session):
        self.session = session

    async def expire_stale_requests(self, stale_hours: int = 24) -> int:
        """
        Find B2B requests that have been in approved_paid status
        for longer than stale_hours, and expire them.

        Returns the count of expired requests.
        """
        cutoff = datetime.utcnow() - timedelta(hours=stale_hours)

        # Find stale approved_paid B2B requests
        result = await self.session.execute(
            select(B2BRequestModel).where(
                B2BRequestModel.status == B2BRequestStatus.approved_paid,
                B2BRequestModel.created_at < cutoff,
            )
        )
        stale_requests = result.scalars().all()

        expired_count = 0
        for req in stale_requests:
            updated = await self.session.execute(
                update(B2BRequestModel)
                .where(
                    B2BRequestModel.id == req.id,
                    B2BRequestModel.status == B2BRequestStatus.approved_paid,
                )
                .values(status=B2BRequestStatus.expired)
            )
            if updated.rowcount > 0:
                expired_count += 1
                logger.info(f"Expired stale B2B request {req.id}")

        logger.info(f"B2B expiry worker: expired {expired_count}/{len(stale_requests)} stale requests")
        return expired_count
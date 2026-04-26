"""
ClaimService — resolves a claim link token and generates a scan JWT for the customer.
Public endpoint: GET /open/claim/{token} — no authentication required.
"""
import secrets
import hashlib
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.allocation.repository import AllocationRepository, ClaimLinkRepository
from apps.allocation.enums import ClaimLinkStatus
from apps.ticketing.models import TicketModel
from apps.event.response import ClaimRedemptionResponse
from src.utils.jwt_utils import generate_scan_jwt
from exceptions import NotFoundError, BadRequestError


class ClaimService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._allocation_repo = AllocationRepository(session)
        self._claim_link_repo = ClaimLinkRepository(session)

    async def get_claim_redemption(self, raw_token: str) -> ClaimRedemptionResponse:
        """
        Resolve a claim link token and return a scan JWT for the customer.

        Flow:
        1. Hash the incoming token (same way we hash during creation)
        2. Look up ClaimLink by token_hash
        3. Verify claim link is active
        4. Query tickets where owner_holder_id = to_holder_id AND event_day_id = claim_link.event_day_id
        5. Generate JTI and return JWT with ticket count

        Returns:
            ClaimRedemptionResponse with holder_id, event_day_id, ticket_count, jwt

        Raises:
            NotFoundError if token invalid or claim link not found
            BadRequestError if claim link is inactive
        """
        # 1. Hash token the same way we did during creation
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        # 2. Look up claim link
        claim_link = await self._claim_link_repo.get_by_token_hash(token_hash)
        if not claim_link:
            raise NotFoundError("Claim link not found")

        # 3. Verify active
        if claim_link.status != ClaimLinkStatus.active:
            raise BadRequestError("Claim link has already been used or revoked")

        # 4. Query tickets owned by to_holder_id for THIS event_day only
        result = await self._session.scalars(
            select(TicketModel)
            .where(
                TicketModel.owner_holder_id == claim_link.to_holder_id,
                TicketModel.event_day_id == claim_link.event_day_id,
                TicketModel.status == "active",
                TicketModel.lock_reference_id.is_(None),
            )
        )
        tickets = list(result.all())

        if not tickets:
            raise NotFoundError("No tickets found for this claim link")

        # Extract sorted indexes (all tickets are for the same event_day)
        indexes = sorted(ticket.ticket_index for ticket in tickets)

        # 5. Generate unique JTI for this JWT
        jti = secrets.token_hex(8)  # 16-char hex string

        # 6. Generate JWT
        jwt = generate_scan_jwt(
            jti=jti,
            holder_id=claim_link.to_holder_id,
            event_day_id=claim_link.event_day_id,
            indexes=indexes,
        )

        # 7. Store JTI in claim link for future revocation
        claim_link.jwt_jti = jti
        await self._session.flush()

        # 8. Return response with ticket count, not indexes
        return ClaimRedemptionResponse(
            holder_id=claim_link.to_holder_id,
            event_day_id=claim_link.event_day_id,
            ticket_count=len(indexes),
            jwt=jwt,
        )

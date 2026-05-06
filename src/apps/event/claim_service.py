"""
ClaimService — resolves a claim link token and generates a scan JWT for the customer.
Public endpoint: GET /open/claim/{token} — no authentication required.
"""
import secrets
import hashlib

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from apps.allocation.enums import AllocationStatus, AllocationType, ClaimLinkStatus
from apps.allocation.repository import (
    AllocationRepository,
    ClaimLinkRepository,
    RevokedScanTokenRepository,
)
from apps.ticketing.models import TicketModel
from apps.ticketing.repository import TicketingRepository
from apps.event.response import ClaimRedemptionResponse, SplitClaimResponse
from src.utils.claim_link_utils import generate_claim_link_token
from src.utils.jwt_utils import generate_scan_jwt
from src.utils.notifications.email import mock_send_email
from exceptions import NotFoundError, BadRequestError


class ClaimService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._allocation_repo = AllocationRepository(session)
        self._claim_link_repo = ClaimLinkRepository(session)
        self._revoked_scan_token_repo = RevokedScanTokenRepository(session)

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

        # 4. Query tickets for this claim link only.
        result = await self._session.scalars(
            select(TicketModel)
            .where(
                TicketModel.claim_link_id == claim_link.id,
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

        # 5. Use the stored JTI.
        jti = claim_link.jwt_jti

        # 7. Generate JWT
        jwt = generate_scan_jwt(
            jti=jti,
            holder_id=claim_link.to_holder_id,
            event_day_id=claim_link.event_day_id,
            indexes=indexes,
        )

        # 8. Return response with ticket count, not indexes
        return ClaimRedemptionResponse(
            ticket_count=len(indexes),
            jwt=jwt,
        )

    async def split_claim(
        self,
        raw_token: str,
        to_email: str,
        ticket_count: int,
    ) -> SplitClaimResponse:
        """
        Split tickets from Customer A to Customer B via claim link.
        """
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        claim_link = await self._claim_link_repo.get_by_token_hash(token_hash)
        if not claim_link:
            raise NotFoundError("Claim link not found")

        if claim_link.status != ClaimLinkStatus.active:
            raise BadRequestError("Claim link has already been used or revoked")

        if ticket_count <= 0:
            raise BadRequestError("Ticket count must be positive")

        customer_a_id = claim_link.to_holder_id
        event_day_id = claim_link.event_day_id
        event_id = claim_link.event_id

        customer_b = await self._allocation_repo.resolve_holder(email=to_email)

        source_allocation = await self._allocation_repo.get_allocation_by_id(
            claim_link.allocation_id
        )
        if not source_allocation:
            raise NotFoundError("Source allocation not found")

        ticketing_repo = TicketingRepository(self._session)
        b2b_ticket_type = await ticketing_repo.get_b2b_ticket_type_for_event(event_id)
        if not b2b_ticket_type:
            raise NotFoundError("B2B ticket type not found")

        result = await self._session.scalars(
            select(TicketModel)
            .where(
                TicketModel.owner_holder_id == customer_a_id,
                TicketModel.event_day_id == event_day_id,
                TicketModel.ticket_type_id == b2b_ticket_type.id,
                TicketModel.status == "active",
                TicketModel.lock_reference_id.is_(None),
            )
            .order_by(TicketModel.ticket_index.asc())
        )
        customer_a_tickets = list(result.all())
        available_count = len(customer_a_tickets)

        if ticket_count > available_count:
            raise BadRequestError(f"Only {available_count} tickets available")

        try:
            locked_ticket_ids = await ticketing_repo.lock_tickets_for_transfer(
                owner_holder_id=customer_a_id,
                event_id=event_id,
                ticket_type_id=b2b_ticket_type.id,
                event_day_id=event_day_id,
                quantity=ticket_count,
                order_id=source_allocation.order_id,
            )
        except ValueError as exc:
            raise BadRequestError(str(exc)) from exc

        customer_b_raw_token = generate_claim_link_token(length=8)
        customer_b_token_hash = hashlib.sha256(customer_b_raw_token.encode()).hexdigest()
        customer_b_jti = secrets.token_hex(8)
        (
            allocation,
            customer_b_claim_link,
        ) = await self._allocation_repo.create_allocation_with_claim_link(
            event_id=event_id,
            event_day_id=event_day_id,
            from_holder_id=customer_a_id,
            to_holder_id=customer_b.id,
            order_id=source_allocation.order_id,
            allocation_type=AllocationType.transfer,
            ticket_count=len(locked_ticket_ids),
            token_hash=customer_b_token_hash,
            created_by_holder_id=customer_a_id,
            jwt_jti=customer_b_jti,
            metadata_={"source": "customer_split"},
        )

        await self._allocation_repo.add_tickets_to_allocation(
            allocation.id,
            locked_ticket_ids,
        )
        await self._allocation_repo.upsert_edge(
            event_id=event_id,
            from_holder_id=customer_a_id,
            to_holder_id=customer_b.id,
            ticket_count=len(locked_ticket_ids),
        )
        await ticketing_repo.update_ticket_ownership_batch(
            ticket_ids=locked_ticket_ids,
            new_owner_holder_id=customer_b.id,
            claim_link_id=customer_b_claim_link.id,
        )
        await self._allocation_repo.transition_allocation_status(
            allocation.id,
            AllocationStatus.pending,
            AllocationStatus.completed,
        )

        # Don't revoke claim link — Customer A's claim URL stays valid forever
        # Only the jwt_jti will be updated with the new JTI
        if claim_link.jwt_jti:
            await self._revoked_scan_token_repo.add_revoked_jti(
                event_day_id=event_day_id,
                jti=claim_link.jwt_jti,
                reason="split",
            )

        transferred_ids = set(locked_ticket_ids)
        remaining_tickets = [
            ticket for ticket in customer_a_tickets if ticket.id not in transferred_ids
        ]
        remaining_indexes = [ticket.ticket_index for ticket in remaining_tickets]

        new_jti = secrets.token_hex(8)
        new_jwt = generate_scan_jwt(
            jti=new_jti,
            holder_id=customer_a_id,
            event_day_id=event_day_id,
            indexes=remaining_indexes,
        )
        claim_link.jwt_jti = new_jti
        await self._session.flush()

        remaining_ids = [ticket.id for ticket in remaining_tickets]
        if remaining_ids:
            await self._session.execute(
                update(TicketModel)
                .where(TicketModel.id.in_(remaining_ids))
                .values(claim_link_id=claim_link.id)
            )

        claim_link_url = f"/claim/{customer_b_raw_token}"
        print(f"\n[CUSTOMER SPLIT] Claim URL: http://0.0.0.0:8080/api/open{claim_link_url}\n")

        # TODO: Re-enable notifications once phone/WhatsApp integration is ready
        # mock_send_whatsapp(to_email, f"Your claim link: {claim_link_url}")
        mock_send_email(
            to_email,
            "Your claim link",
            f"Your claim link: {claim_link_url}",
        )

        return SplitClaimResponse(
            status="completed",
            tickets_transferred=len(locked_ticket_ids),
            remaining_ticket_count=len(remaining_tickets),
            new_jwt=new_jwt,
            message="Your previous QR code is no longer valid. Please use the new QR code for entry.",
        )

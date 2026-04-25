from typing import Optional
from uuid import UUID

from sqlalchemy import select, update, func, or_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from apps.ticketing.models import TicketModel, TicketTypeModel
from .enums import AllocationStatus, AllocationType, ClaimLinkStatus
from .models import AllocationEdgeModel, AllocationModel, AllocationTicketModel, TicketHolderModel, ClaimLinkModel, RevokedScanTokenModel


class AllocationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

    # --- TicketHolder ---

    async def get_holder_by_id(self, holder_id: UUID) -> Optional[TicketHolderModel]:
        return await self._session.scalar(
            select(TicketHolderModel).where(TicketHolderModel.id == holder_id)
        )

    async def get_holder_by_user_id(self, user_id: UUID) -> Optional[TicketHolderModel]:
        return await self._session.scalar(
            select(TicketHolderModel).where(TicketHolderModel.user_id == user_id)
        )

    async def get_holder_by_phone(self, phone: str) -> Optional[TicketHolderModel]:
        return await self._session.scalar(
            select(TicketHolderModel).where(TicketHolderModel.phone == phone)
        )

    async def get_holder_by_email(self, email: str) -> Optional[TicketHolderModel]:
        return await self._session.scalar(
            select(TicketHolderModel).where(TicketHolderModel.email == email)
        )

    async def create_holder(
        self,
        user_id: UUID | None = None,
        phone: str | None = None,
        email: str | None = None,
    ) -> TicketHolderModel:
        holder = TicketHolderModel(user_id=user_id, phone=phone, email=email)
        self._session.add(holder)
        await self._session.flush()
        await self._session.refresh(holder)
        return holder

    async def resolve_holder(
        self,
        phone: str | None = None,
        email: str | None = None,
        user_id: UUID | None = None,
    ) -> TicketHolderModel:
        """
        Get or create a TicketHolder by phone, email, or user_id.
        At least one of phone, email, or user_id must be provided.
        """
        if phone:
            holder = await self.get_holder_by_phone(phone)
            if holder:
                return holder

        if email:
            holder = await self.get_holder_by_email(email)
            if holder:
                return holder

        if user_id:
            holder = await self.get_holder_by_user_id(user_id)
            if holder:
                return holder

        # Create new holder
        return await self.create_holder(
            user_id=user_id,
            phone=phone,
            email=email,
        )

    # --- Allocation ---

    async def get_allocation_by_id(self, allocation_id: UUID) -> Optional[AllocationModel]:
        return await self._session.scalar(
            select(AllocationModel).where(AllocationModel.id == allocation_id)
        )

    async def create_allocation(
        self,
        event_id: UUID,
        from_holder_id: UUID | None,
        to_holder_id: UUID,
        order_id: UUID,
        allocation_type: "AllocationType",
        ticket_count: int = 0,
        metadata_: dict | None = None,
    ) -> AllocationModel:
        allocation = AllocationModel(
            event_id=event_id,
            from_holder_id=from_holder_id,
            to_holder_id=to_holder_id,
            order_id=order_id,
            allocation_type=allocation_type,
            ticket_count=ticket_count,
            metadata_=metadata_ or {},
        )
        self._session.add(allocation)
        await self._session.flush()
        await self._session.refresh(allocation)
        return allocation

    async def transition_allocation_status(
        self,
        allocation_id: UUID,
        expected_current: AllocationStatus,
        new_status: AllocationStatus,
        failure_reason: str | None = None,
    ) -> bool:
        """
        Atomically transition allocation status only if currently in expected state.
        Returns True if transition succeeded.
        """
        kwargs = {"status": new_status.value}
        if failure_reason is not None:
            kwargs["failure_reason"] = failure_reason

        result = await self._session.execute(
            update(AllocationModel)
            .where(
                AllocationModel.id == allocation_id,
                AllocationModel.status == expected_current.value,
            )
            .values(**kwargs)
            .returning(AllocationModel.id)
        )
        return result.scalar_one_or_none() is not None

    # --- AllocationTicket ---

    async def add_tickets_to_allocation(
        self,
        allocation_id: UUID,
        ticket_ids: list[UUID],
    ) -> list[AllocationTicketModel]:
        records = [
            AllocationTicketModel(allocation_id=allocation_id, ticket_id=tid)
            for tid in ticket_ids
        ]
        self._session.add_all(records)
        await self._session.flush()
        return records

    async def create_allocation_with_claim_link(
        self,
        event_id: UUID,
        event_day_id: UUID,
        from_holder_id: UUID | None,
        to_holder_id: UUID,
        order_id: UUID,
        allocation_type: "AllocationType",
        ticket_count: int,
        token_hash: str,
        created_by_holder_id: UUID,
        metadata_: dict | None = None,
    ) -> tuple[AllocationModel, ClaimLinkModel]:
        """
        Create an allocation and its associated claim link in a single transaction.
        Returns (allocation, claim_link).

        The claim link is created for the recipient (to_holder_id).
        The claim link is scoped to a specific event_day_id.
        """
        allocation = await self.create_allocation(
            event_id=event_id,
            from_holder_id=from_holder_id,
            to_holder_id=to_holder_id,
            order_id=order_id,
            allocation_type=allocation_type,
            ticket_count=ticket_count,
            metadata_=metadata_,
        )

        claim_link = await ClaimLinkRepository(self._session).create(
            allocation_id=allocation.id,
            token_hash=token_hash,
            event_id=event_id,
            event_day_id=event_day_id,
            from_holder_id=from_holder_id,
            to_holder_id=to_holder_id,
            created_by_holder_id=created_by_holder_id,
        )

        return allocation, claim_link

    # --- AllocationEdge ---

    async def upsert_edge(
        self,
        event_id: UUID,
        from_holder_id: UUID | None,
        to_holder_id: UUID,
        ticket_count: int,
    ) -> None:
        """
        Upsert allocation edge with atomic increment.
        Uses ON CONFLICT DO UPDATE to increment ticket_count.
        """
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from sqlalchemy import text

        stmt = pg_insert(AllocationEdgeModel).values(
            event_id=event_id,
            from_holder_id=from_holder_id,
            to_holder_id=to_holder_id,
            ticket_count=ticket_count,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_allocation_edges_event_from_to",
            set_={
                "ticket_count": AllocationEdgeModel.ticket_count + stmt.excluded.ticket_count,
                "updated_at": func.now(),
            },
        )
        await self._session.execute(stmt)

    # --- B2B Organizer Queries ---

    async def list_b2b_tickets_by_holder(
        self,
        event_id: UUID,
        holder_id: UUID,
        b2b_ticket_type_id: UUID,
        event_day_id: UUID | None = None,
    ) -> list[dict]:
        """
        List B2B ticket counts owned by a holder for an event, grouped by event_day.
        Uses COUNT + GROUP BY — does NOT return full ticket rows.

        Args:
            event_id: Event UUID
            holder_id: TicketHolder UUID
            b2b_ticket_type_id: The B2B ticket type UUID for this event
            event_day_id: Optional -- if provided, filter to specific day only
        """
        conditions = [
            TicketModel.event_id == event_id,
            TicketModel.owner_holder_id == holder_id,
            TicketModel.ticket_type_id == b2b_ticket_type_id,
            TicketModel.lock_reference_id.is_(None),  # Only count unlocked tickets
        ]
        if event_day_id:
            conditions.append(TicketModel.event_day_id == event_day_id)

        result = await self._session.execute(
            select(
                TicketModel.event_day_id,
                func.count(TicketModel.id).label("count"),
            )
            .where(*conditions)
            .group_by(
                TicketModel.event_day_id,
            )
        )
        rows = result.all()
        return [
            {
                "event_day_id": row[0],
                "count": row[1],
            }
            for row in rows
        ]

    async def list_b2b_allocations_for_holder(
        self,
        event_id: UUID,
        holder_id: UUID,
        event_day_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """
        List B2B allocations where the given holder is sender or receiver.
        Returns event_day_id per allocation. Single query, no N+1.

        Args:
            event_id: Event UUID
            holder_id: TicketHolder UUID
            event_day_id: Optional -- if provided, filter allocations to tickets from that day only
            limit: Pagination limit
            offset: Pagination offset
        """
        from apps.ticketing.models import TicketModel

        # Subquery: filter allocations to those involving this holder
        alloc_filter = (
            select(AllocationModel.id)
            .where(
                AllocationModel.event_id == event_id,
                AllocationModel.allocation_type == AllocationType.b2b,
                or_(
                    AllocationModel.to_holder_id == holder_id,
                    AllocationModel.from_holder_id == holder_id,
                ),
            )
            .order_by(AllocationModel.created_at.desc())
            .limit(limit)
            .offset(offset)
            .subquery()
        )

        # Subquery: get event_day_id from first ticket in each allocation
        day_subq = (
            select(
                AllocationTicketModel.allocation_id,
                TicketModel.event_day_id,
            )
            .join(TicketModel, AllocationTicketModel.ticket_id == TicketModel.id)
            .where(AllocationTicketModel.allocation_id.in_(select(alloc_filter)))
            .distinct(AllocationTicketModel.allocation_id)
            .subquery()
        )

        # Main query: allocations with event_day_id
        result = await self._session.execute(
            select(AllocationModel, day_subq.c.event_day_id)
            .join(day_subq, AllocationModel.id == day_subq.c.allocation_id)
            .order_by(AllocationModel.created_at.desc())
        )
        rows = result.all()

        enriched = []
        for alloc, day_id in rows:
            direction = "received" if alloc.to_holder_id == holder_id else "transferred"
            metadata = alloc.metadata_ or {}
            source = metadata.get("source", "b2b_free")

            enriched.append({
                "allocation_id": alloc.id,
                "event_day_id": day_id,
                "direction": direction,
                "from_holder_id": alloc.from_holder_id,
                "to_holder_id": alloc.to_holder_id,
                "ticket_count": alloc.ticket_count,
                "status": alloc.status,
                "source": source,
                "created_at": alloc.created_at,
            })

        return enriched


class ClaimLinkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        allocation_id: UUID,
        token_hash: str,
        event_id: UUID,
        event_day_id: UUID,
        from_holder_id: UUID | None,
        to_holder_id: UUID,
        created_by_holder_id: UUID,
    ) -> ClaimLinkModel:
        """Create a new claim link scoped to a specific event_day."""
        link = ClaimLinkModel(
            allocation_id=allocation_id,
            token_hash=token_hash,
            event_id=event_id,
            event_day_id=event_day_id,
            from_holder_id=from_holder_id,
            to_holder_id=to_holder_id,
            status=ClaimLinkStatus.active,
            created_by_holder_id=created_by_holder_id,
        )
        self._session.add(link)
        await self._session.flush()
        await self._session.refresh(link)
        return link

    async def get_by_token_hash(self, token_hash: str) -> ClaimLinkModel | None:
        """Get a claim link by its token hash."""
        return await self._session.scalar(
            select(ClaimLinkModel).where(ClaimLinkModel.token_hash == token_hash)
        )

    async def get_active_by_to_holder(self, to_holder_id: UUID) -> ClaimLinkModel | None:
        """Get the active claim link for a recipient holder."""
        return await self._session.scalar(
            select(ClaimLinkModel)
            .where(
                ClaimLinkModel.to_holder_id == to_holder_id,
                ClaimLinkModel.status == ClaimLinkStatus.active,
            )
            .order_by(ClaimLinkModel.created_at.desc())
        )

    async def revoke(self, token_hash: str) -> bool:
        """
        Revoke a claim link by setting status to inactive.
        Returns True if revocation succeeded.
        """
        result = await self._session.execute(
            update(ClaimLinkModel)
            .where(
                ClaimLinkModel.token_hash == token_hash,
                ClaimLinkModel.status == ClaimLinkStatus.active,
            )
            .values(status=ClaimLinkStatus.inactive)
        )
        return result.rowcount > 0


class RevokedScanTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_revoked(
        self,
        event_day_id: UUID,
        jti: str,
        reason: str,
    ) -> None:
        """
        Add a JTI to the revoked tokens table.
        Uses ON CONFLICT DO NOTHING to handle duplicate revocations gracefully.
        """
        stmt = pg_insert(RevokedScanTokenModel).values(
            event_day_id=event_day_id,
            jti=jti,
            reason=reason,
        )
        stmt = stmt.on_conflict_do_nothing(
            constraint="uq_revoked_scan_tokens_event_day_jti",
        )
        await self._session.execute(stmt)

    async def is_revoked(self, event_day_id: UUID, jti: str) -> bool:
        """Check if a JTI has been revoked for a given event day."""
        result = await self._session.scalar(
            select(RevokedScanTokenModel.jti).where(
                RevokedScanTokenModel.event_day_id == event_day_id,
                RevokedScanTokenModel.jti == jti,
            )
        )
        return result is not None

    async def get_revoked_jtis_for_event_day(
        self,
        event_day_id: UUID,
    ) -> list[str]:
        """Get all revoked JTI strings for an event day."""
        result = await self._session.scalars(
            select(RevokedScanTokenModel.jti).where(
                RevokedScanTokenModel.event_day_id == event_day_id,
            )
        )
        return list(result.all())

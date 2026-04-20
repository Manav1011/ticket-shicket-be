from datetime import date
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from apps.organizer.models import OrganizerPageModel
from apps.ticketing.models import DayTicketAllocationModel, TicketTypeModel
from apps.user.invite.models import InviteModel

from .models import EventDayModel, EventModel, EventInterestModel, ScanStatusHistoryModel, EventMediaAssetModel, EventResellerModel


class EventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

    def add(self, entity) -> None:
        self._session.add(entity)

    async def get_by_id_for_owner(
        self, event_id: UUID, owner_user_id: UUID
    ) -> Optional[EventModel]:
        return await self._session.scalar(
            select(EventModel)
            .join_from(EventModel, OrganizerPageModel)
            .where(
                EventModel.id == event_id,
                OrganizerPageModel.owner_user_id == owner_user_id,
            )
        )

    async def get_by_id(self, event_id: UUID) -> Optional[EventModel]:
        return await self._session.scalar(
            select(EventModel).where(EventModel.id == event_id)
        )

    async def get_by_id_for_update(self, event_id: UUID) -> Optional[EventModel]:
        return await self._session.scalar(
            select(EventModel).where(EventModel.id == event_id).with_for_update()
        )

    async def create_event_day(
        self, event_id, day_date, start_time=None, end_time=None
    ) -> EventDayModel:
        result = await self._session.execute(
            update(EventModel)
            .where(EventModel.id == event_id)
            .values(days_count=EventModel.days_count + 1)
            .returning(EventModel.days_count)
        )
        day_index = result.scalar_one_or_none()
        if day_index is None:
            raise ValueError(f"Event {event_id} not found")

        event_day = EventDayModel(
            event_id=event_id,
            day_index=day_index,
            date=day_date,
            start_time=start_time,
            end_time=end_time,
            scan_status="not_started",
            next_ticket_index=1,
        )
        self._session.add(event_day)
        await self._session.flush()
        await self._session.refresh(event_day)
        return event_day

    async def get_event_day_for_owner(
        self, event_day_id: UUID, owner_user_id: UUID
    ) -> Optional[EventDayModel]:
        return await self._session.scalar(
            select(EventDayModel)
            .join(EventModel, EventDayModel.event_id == EventModel.id)
            .join_from(EventModel, OrganizerPageModel)
            .where(
                EventDayModel.id == event_day_id,
                OrganizerPageModel.owner_user_id == owner_user_id,
            )
        )

    async def get_event_day_by_id(self, event_day_id: UUID) -> Optional[EventDayModel]:
        """Get an event day by ID without ownership check."""
        return await self._session.scalar(
            select(EventDayModel).where(EventDayModel.id == event_day_id)
        )

    async def list_event_days(self, event_id: UUID) -> list[EventDayModel]:
        result = await self._session.scalars(
            select(EventDayModel)
            .where(EventDayModel.event_id == event_id)
            .order_by(EventDayModel.day_index.asc())
        )
        return list(result.all())

    async def delete_event_day(self, event_day: EventDayModel) -> None:
        await self._session.delete(event_day)
        await self._session.flush()
        await self._session.execute(
            update(EventModel)
            .where(EventModel.id == event_day.event_id)
            .values(days_count=EventModel.days_count - 1)
        )
        await self._session.flush()

    async def count_event_days(self, event_id: UUID) -> int:
        return await self._session.scalar(
            select(func.count(EventDayModel.id)).where(EventDayModel.event_id == event_id)
        )

    async def count_ticket_types(self, event_id: UUID) -> int:
        return await self._session.scalar(
            select(func.count(TicketTypeModel.id)).where(TicketTypeModel.event_id == event_id)
        )

    async def count_ticket_allocations(self, event_id: UUID) -> int:
        return await self._session.scalar(
            select(func.count(DayTicketAllocationModel.id))
            .join(TicketTypeModel, DayTicketAllocationModel.ticket_type_id == TicketTypeModel.id)
            .where(TicketTypeModel.event_id == event_id)
        )

    async def list_ticket_types(self, event_id: UUID) -> list[TicketTypeModel]:
        result = await self._session.scalars(
            select(TicketTypeModel)
            .where(TicketTypeModel.event_id == event_id)
            .order_by(TicketTypeModel.created_at.asc())
        )
        return list(result.all())

    async def list_allocations(self, event_id: UUID) -> list[DayTicketAllocationModel]:
        result = await self._session.scalars(
            select(DayTicketAllocationModel)
            .join(TicketTypeModel, DayTicketAllocationModel.ticket_type_id == TicketTypeModel.id)
            .where(TicketTypeModel.event_id == event_id)
            .order_by(DayTicketAllocationModel.created_at.asc())
        )
        return list(result.all())

    async def create_scan_status_history(
        self,
        event_day_id: UUID,
        changed_by_user_id: UUID,
        previous_status: str,
        new_status: str,
        notes: str | None = None,
    ) -> ScanStatusHistoryModel:
        history = ScanStatusHistoryModel(
            event_day_id=event_day_id,
            changed_by_user_id=changed_by_user_id,
            previous_status=previous_status,
            new_status=new_status,
            notes=notes,
        )
        self._session.add(history)
        await self._session.flush()
        await self._session.refresh(history)
        return history

    async def list_scan_status_history(
        self, event_day_id: UUID
    ) -> list[ScanStatusHistoryModel]:
        result = await self._session.scalars(
            select(ScanStatusHistoryModel)
            .where(ScanStatusHistoryModel.event_day_id == event_day_id)
            .order_by(ScanStatusHistoryModel.created_at.desc())
        )
        return list(result.all())

    async def list_media_assets(
        self, event_id: UUID, asset_type: str | None = None
    ) -> list[EventMediaAssetModel]:
        """List media assets for event, optionally filtered by type."""
        query = select(EventMediaAssetModel).where(
            EventMediaAssetModel.event_id == event_id
        )

        if asset_type:
            query = query.where(EventMediaAssetModel.asset_type == asset_type)

        query = query.order_by(
            EventMediaAssetModel.sort_order.asc(), EventMediaAssetModel.created_at.asc()
        )

        result = await self._session.scalars(query)
        return list(result.all())

    async def get_media_asset_by_id(self, asset_id: UUID) -> Optional[EventMediaAssetModel]:
        """Get media asset by ID."""
        return await self._session.scalar(
            select(EventMediaAssetModel).where(EventMediaAssetModel.id == asset_id)
        )

    async def delete_media_asset(self, asset: EventMediaAssetModel) -> None:
        """Delete media asset from database."""
        await self._session.delete(asset)
        await self._session.flush()

    async def get_interest_for_actor(
        self,
        event_id: UUID,
        user_id: UUID | None = None,
        guest_id: UUID | None = None,
    ) -> EventInterestModel | None:
        query = select(EventInterestModel).where(EventInterestModel.event_id == event_id)
        if user_id is not None:
            query = query.where(EventInterestModel.user_id == user_id)
        if guest_id is not None:
            query = query.where(EventInterestModel.guest_id == guest_id)
        return await self._session.scalar(query)

    async def create_event_interest(
        self,
        event_id: UUID,
        user_id: UUID | None,
        guest_id: UUID | None,
        ip_address: str,
        user_agent: str | None,
    ) -> EventInterestModel:
        interest = EventInterestModel(
            event_id=event_id,
            user_id=user_id,
            guest_id=guest_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self._session.add(interest)
        await self._session.flush()
        await self._session.refresh(interest)
        return interest

    async def increment_event_interest_counter(self, event_id: UUID) -> None:
        await self._session.execute(
            update(EventModel)
            .where(EventModel.id == event_id)
            .values(interested_counter=EventModel.interested_counter + 1)
        )

    async def create_event_reseller(
        self,
        user_id: UUID,
        event_id: UUID,
        invited_by_id: UUID,
        permissions: dict,
    ) -> EventResellerModel:
        from datetime import datetime
        reseller = EventResellerModel(
            user_id=user_id,
            event_id=event_id,
            invited_by_id=invited_by_id,
            permissions=permissions,
            accepted_at=datetime.utcnow(),
        )
        self._session.add(reseller)
        await self._session.flush()
        await self._session.refresh(reseller)
        return reseller

    async def get_reseller_for_event(
        self, user_id: UUID, event_id: UUID
    ) -> Optional[EventResellerModel]:
        return await self._session.scalar(
            select(EventResellerModel).where(
                and_(
                    EventResellerModel.user_id == user_id,
                    EventResellerModel.event_id == event_id,
                )
            )
        )

    async def list_resellers_for_event(self, event_id: UUID) -> list[EventResellerModel]:
        result = await self._session.scalars(
            select(EventResellerModel)
            .where(EventResellerModel.event_id == event_id)
            .order_by(EventResellerModel.created_at.desc())
        )
        return list(result.all())

    async def list_reseller_invites_for_event(
        self,
        event_id: UUID,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[InviteModel]:
        """List invites for an event, optionally filtered by status."""
        from apps.user.invite.enums import InviteType

        query = select(InviteModel).where(
            and_(
                InviteModel.meta.contains({"event_id": str(event_id)}),
                InviteModel.invite_type == InviteType.reseller.value,
            )
        )
        if status:
            query = query.where(InviteModel.status == status)

        query = query.order_by(InviteModel.created_at.desc()).limit(limit).offset(offset)
        result = await self._session.scalars(query)
        return list(result.all())

    async def list_published_events(self) -> list[EventModel]:
        result = await self._session.scalars(
            select(EventModel)
            .where(EventModel.is_published == True)
            .where(EventModel.status == "published")
            .order_by(EventModel.created_at.desc())
        )
        return list(result.all())

    async def list_events_for_user(
        self,
        owner_user_id: UUID,
        status: str | None = None,
        event_access_type: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        search: str | None = None,
        sort_by: str = "created_at",
        order: str = "desc",
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[EventModel], int]:
        """
        List all events for a user across all their organizer pages.
        Returns (events, total_count). Optimized — uses index on organizer_page_id + owner_user_id.
        """
        # Base conditions: event belongs to an organizer page owned by this user
        conditions = [
            OrganizerPageModel.owner_user_id == owner_user_id,
        ]

        if status is not None:
            conditions.append(EventModel.status == status)
        if event_access_type is not None:
            conditions.append(EventModel.event_access_type == event_access_type)
        if date_from is not None:
            conditions.append(EventModel.start_date >= date_from)
        if date_to is not None:
            conditions.append(EventModel.start_date <= date_to)
        if search is not None:
            conditions.append(EventModel.title.ilike(f"%{search}%"))

        # Sorting
        sort_column = {
            "created_at": EventModel.created_at,
            "start_date": EventModel.start_date,
            "title": EventModel.title,
            "status": EventModel.status,
        }.get(sort_by, EventModel.created_at)

        if order == "asc":
            query = select(EventModel).join_from(EventModel, OrganizerPageModel).where(*conditions).order_by(sort_column.asc())
        else:
            query = select(EventModel).join_from(EventModel, OrganizerPageModel).where(*conditions).order_by(sort_column.desc())

        # Count total
        count_query = select(func.count(EventModel.id)).join_from(EventModel, OrganizerPageModel).where(*conditions)
        total = await self._session.scalar(count_query) or 0

        # Paginated results
        query = query.limit(limit).offset(offset)
        result = await self._session.scalars(query)
        events = list(result.all())

        return events, total

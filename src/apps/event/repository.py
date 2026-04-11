from typing import Optional
from uuid import UUID

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from apps.organizer.models import OrganizerPageModel
from apps.ticketing.models import DayTicketAllocationModel, TicketTypeModel

from .models import EventDayModel, EventModel, ScanStatusHistoryModel, EventMediaAssetModel, EventResellerModel


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

    async def create_event_day(
        self, event_id, day_index, day_date, start_time=None, end_time=None
    ) -> EventDayModel:
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

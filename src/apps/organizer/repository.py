from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.event.models import EventModel
from apps.superadmin.models import B2BRequestModel
from apps.superadmin.repository import SuperAdminRepository

from .models import OrganizerPageModel


class OrganizerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._super_admin_repo = SuperAdminRepository(session)

    @property
    def session(self) -> AsyncSession:
        return self._session

    async def get_by_slug(self, slug: str) -> Optional[OrganizerPageModel]:
        return await self._session.scalar(
            select(OrganizerPageModel).where(OrganizerPageModel.slug == slug)
        )

    async def list_by_owner(self, owner_user_id: UUID) -> list[OrganizerPageModel]:
        result = await self._session.scalars(
            select(OrganizerPageModel)
            .where(OrganizerPageModel.owner_user_id == owner_user_id)
            .order_by(OrganizerPageModel.created_at.desc())
        )
        return list(result.all())

    async def list_events_for_owner(
        self, owner_user_id: UUID, organizer_id: UUID, status: str | None = None
    ) -> list[EventModel]:
        query = (
            select(EventModel)
            .join_from(EventModel, OrganizerPageModel)
            .where(
                EventModel.organizer_page_id == organizer_id,
                OrganizerPageModel.owner_user_id == owner_user_id,
            )
            .order_by(EventModel.created_at.desc())
        )
        if status is not None:
            query = query.where(EventModel.status == status)
        result = await self._session.scalars(query)
        return list(result.all())

    async def get_by_id_for_owner(
        self, organizer_id: UUID, owner_user_id: UUID
    ) -> Optional[OrganizerPageModel]:
        return await self._session.scalar(
            select(OrganizerPageModel).where(
                OrganizerPageModel.id == organizer_id,
                OrganizerPageModel.owner_user_id == owner_user_id,
            )
        )

    def add(self, organizer: OrganizerPageModel) -> None:
        self._session.add(organizer)

    async def get_by_id(self, organizer_id: UUID) -> Optional[OrganizerPageModel]:
        return await self._session.scalar(
            select(OrganizerPageModel).where(OrganizerPageModel.id == organizer_id)
        )

    async def list_public_organizers(self) -> list[OrganizerPageModel]:
        result = await self._session.scalars(
            select(OrganizerPageModel)
            .where(OrganizerPageModel.status == "active")
            .order_by(OrganizerPageModel.created_at.desc())
        )
        return list(result.all())

    async def list_events_by_organizer_public(self, organizer_id: UUID) -> list[EventModel]:
        result = await self._session.scalars(
            select(EventModel)
            .where(
                EventModel.organizer_page_id == organizer_id,
                EventModel.is_published == True,
                EventModel.status == "published",
            )
            .order_by(EventModel.created_at.desc())
        )
        return list(result.all())

    # --- B2B Request Methods ---

    async def create_b2b_request(
        self,
        requesting_organizer_id: UUID,
        requesting_user_id: UUID,
        event_id: UUID,
        event_day_id: UUID,
        ticket_type_id: UUID,
        quantity: int,
        recipient_phone: str | None = None,
        recipient_email: str | None = None,
    ) -> B2BRequestModel:
        return await self._super_admin_repo.create_b2b_request(
            requesting_organizer_id=requesting_organizer_id,
            requesting_user_id=requesting_user_id,
            event_id=event_id,
            event_day_id=event_day_id,
            ticket_type_id=ticket_type_id,
            quantity=quantity,
            recipient_phone=recipient_phone,
            recipient_email=recipient_email,
        )

    async def get_b2b_request_by_id(
        self, request_id: UUID
    ) -> Optional[B2BRequestModel]:
        return await self._super_admin_repo.get_b2b_request_by_id(request_id)

    async def list_b2b_requests_by_organizer(
        self,
        organizer_id: UUID,
        status: Optional = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[B2BRequestModel]:
        return await self._super_admin_repo.list_b2b_requests_by_organizer(
            organizer_id=organizer_id,
            status=status,
            limit=limit,
            offset=offset,
        )

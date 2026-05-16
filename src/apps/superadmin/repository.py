from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .enums import B2BRequestStatus
from .models import B2BRequestModel, SuperAdminModel
from apps.ticketing.models import TicketTypeModel
from apps.event.models import EventModel, EventDayModel
from apps.user.models import UserModel
from sqlalchemy import select

class SuperAdminRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

    # --- SuperAdmin ---

    async def get_super_admin_by_user_id(self, user_id: UUID) -> Optional[SuperAdminModel]:
        return await self._session.scalar(
            select(SuperAdminModel).where(SuperAdminModel.user_id == user_id)
        )

    async def create_super_admin(self, user_id: UUID, name: str) -> SuperAdminModel:
        admin = SuperAdminModel(user_id=user_id, name=name)
        self._session.add(admin)
        await self._session.flush()
        await self._session.refresh(admin)
        return admin

    # --- B2B Request ---

    async def get_b2b_request_by_id(self, request_id: UUID) -> Optional[B2BRequestModel]:
        return await self._session.scalar(
            select(B2BRequestModel).where(B2BRequestModel.id == request_id)
        )

    async def get_b2b_request_enriched(self, request_id: UUID) -> Optional[dict]:
        """Get B2B request with event, event_day, ticket_type, and user data in a single query."""

        query = (
            select(
                B2BRequestModel.id,
                B2BRequestModel.quantity,
                B2BRequestModel.status,
                B2BRequestModel.admin_notes,
                B2BRequestModel.created_at,
                B2BRequestModel.updated_at,
                EventModel.title.label("event_name"),
                EventDayModel.date.label("event_day_date"),
                TicketTypeModel.name.label("ticket_type_name"),
                UserModel.email.label("requesting_user_email"),
            )
            .select_from(B2BRequestModel)
            .join(EventModel, B2BRequestModel.event_id == EventModel.id)
            .join(EventDayModel, B2BRequestModel.event_day_id == EventDayModel.id)
            .join(TicketTypeModel, B2BRequestModel.ticket_type_id == TicketTypeModel.id)
            .join(UserModel, B2BRequestModel.requesting_user_id == UserModel.id)
            .where(B2BRequestModel.id == request_id)
        )

        result = await self._session.execute(query)
        row = result.first()

        if not row:
            return None

        return {
            "id": row.id,
            "quantity": row.quantity,
            "status": row.status,
            "admin_notes": row.admin_notes,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
            "event_name": row.event_name,
            "event_day_date": row.event_day_date,
            "ticket_type_name": row.ticket_type_name,
            "requesting_user_email": row.requesting_user_email,
        }

    async def list_b2b_requests(
        self,
        status: B2BRequestStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[B2BRequestModel]:
        query = select(B2BRequestModel).order_by(B2BRequestModel.created_at.desc())
        if status:
            query = query.where(B2BRequestModel.status == status.value)
        query = query.limit(limit).offset(offset)
        result = await self._session.scalars(query)
        return list(result.all())

    async def list_b2b_requests_by_event(
        self,
        event_id: UUID,
        status: B2BRequestStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[B2BRequestModel]:
        query = (
            select(B2BRequestModel)
            .where(B2BRequestModel.event_id == event_id)
            .order_by(B2BRequestModel.created_at.desc())
        )
        if status:
            query = query.where(B2BRequestModel.status == status.value)
        query = query.limit(limit).offset(offset)
        result = await self._session.scalars(query)
        return list(result.all())

    async def create_b2b_request(
        self,
        requesting_user_id: UUID,
        event_id: UUID,
        event_day_id: UUID,
        ticket_type_id: UUID,
        quantity: int,
        metadata: dict | None = None,
    ) -> B2BRequestModel:
        request = B2BRequestModel(
            requesting_user_id=requesting_user_id,
            event_id=event_id,
            event_day_id=event_day_id,
            ticket_type_id=ticket_type_id,
            quantity=quantity,
            metadata_=metadata or {},
        )
        self._session.add(request)
        await self._session.flush()
        await self._session.refresh(request)
        return request

    async def update_b2b_request_status(
        self,
        request_id: UUID,
        new_status: B2BRequestStatus,
        admin_id: UUID,
        admin_notes: str | None = None,
        allocation_id: UUID | None = None,
        order_id: UUID | None = None,
    ) -> bool:
        result = await self._session.execute(
            update(B2BRequestModel)
            .where(B2BRequestModel.id == request_id)
            .values(
                status=new_status.value,
                reviewed_by_admin_id=admin_id,
                admin_notes=admin_notes,
                allocation_id=allocation_id,
                order_id=order_id,
            )
        )
        return result.rowcount > 0

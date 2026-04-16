from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .enums import B2BRequestStatus
from .models import B2BRequestModel, SuperAdminModel


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

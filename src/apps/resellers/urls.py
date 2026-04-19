from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependencies import get_current_user
from db.session import db_session
from utils.schema import BaseResponse

from .repository import ResellerRepository
from .response import ResellerEventsResponse, ResellerTicketsResponse, ResellerAllocationsResponse
from .service import ResellerService

router = APIRouter(
    prefix="/api/resellers", tags=["Resellers"], dependencies=[Depends(get_current_user)]
)


def get_reseller_service(
    session: Annotated[AsyncSession, Depends(db_session)],
) -> ResellerService:
    return ResellerService(session)


@router.get("/events")
async def list_my_reseller_events(
    request: Request,
    service: Annotated[ResellerService, Depends(get_reseller_service)],
) -> ResellerEventsResponse:
    """List events where I'm an accepted reseller."""
    return await service.list_my_events(request.state.user.id)


@router.get("/events/{event_id}/tickets")
async def get_my_reseller_tickets(
    event_id: UUID,
    request: Request,
    service: Annotated[ResellerService, Depends(get_reseller_service)],
) -> ResellerTicketsResponse:
    """Get my tickets for an event I resell."""
    return await service.get_my_tickets(event_id, request.state.user.id)


@router.get("/events/{event_id}/my-allocations")
async def get_my_reseller_allocations(
    event_id: UUID,
    request: Request,
    service: Annotated[ResellerService, Depends(get_reseller_service)],
    limit: int = 50,
    offset: int = 0,
) -> ResellerAllocationsResponse:
    """Get my allocations for an event I resell."""
    return await service.get_my_allocations(event_id, request.state.user.id, limit, offset)

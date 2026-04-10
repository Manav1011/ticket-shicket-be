from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependencies import get_current_user
from db.session import db_session
from utils.schema import BaseResponse

from apps.event.repository import EventRepository
from .repository import TicketingRepository
from .request import (
    AllocateTicketTypeRequest,
    CreateTicketTypeRequest,
    UpdateTicketAllocationQuantityRequest,
)
from .response import DayTicketAllocationResponse, TicketTypeResponse
from .service import TicketingService

router = APIRouter(
    prefix="/api/events", tags=["Ticketing"], dependencies=[Depends(get_current_user)]
)


def get_ticketing_service(
    session: Annotated[AsyncSession, Depends(db_session)],
) -> TicketingService:
    event_repository = EventRepository(session)
    return TicketingService(TicketingRepository(session), event_repository, event_repository)


@router.get("/{event_id}/ticket-types")
async def list_ticket_types(
    event_id: UUID,
    request: Request,
    service: Annotated[TicketingService, Depends(get_ticketing_service)],
) -> BaseResponse[list[TicketTypeResponse]]:
    ticket_types = await service.list_ticket_types(request.state.user.id, event_id)
    return BaseResponse(data=[TicketTypeResponse.model_validate(item) for item in ticket_types])


@router.post("/{event_id}/ticket-types")
async def create_ticket_type(
    event_id: UUID,
    request: Request,
    body: Annotated[CreateTicketTypeRequest, Body()],
    service: Annotated[TicketingService, Depends(get_ticketing_service)],
) -> BaseResponse[TicketTypeResponse]:
    ticket_type = await service.create_ticket_type(
        request.state.user.id, event_id, **body.model_dump()
    )
    return BaseResponse(data=TicketTypeResponse.model_validate(ticket_type))


@router.get("/{event_id}/ticket-allocations")
async def list_ticket_allocations(
    event_id: UUID,
    request: Request,
    service: Annotated[TicketingService, Depends(get_ticketing_service)],
) -> BaseResponse[list[DayTicketAllocationResponse]]:
    allocations = await service.list_allocations(request.state.user.id, event_id)
    return BaseResponse(
        data=[DayTicketAllocationResponse.model_validate(item) for item in allocations]
    )


@router.post("/{event_id}/ticket-allocations")
async def create_ticket_allocation(
    event_id: UUID,
    request: Request,
    body: Annotated[AllocateTicketTypeRequest, Body()],
    service: Annotated[TicketingService, Depends(get_ticketing_service)],
) -> BaseResponse[DayTicketAllocationResponse]:
    allocation = await service.allocate_ticket_type_to_day(
        request.state.user.id, event_id, **body.model_dump()
    )
    return BaseResponse(data=DayTicketAllocationResponse.model_validate(allocation))


@router.patch("/{event_id}/ticket-allocations/{allocation_id}")
async def update_ticket_allocation_quantity(
    event_id: UUID,
    allocation_id: UUID,
    request: Request,
    body: Annotated[UpdateTicketAllocationQuantityRequest, Body()],
    service: Annotated[TicketingService, Depends(get_ticketing_service)],
) -> BaseResponse[DayTicketAllocationResponse]:
    allocation = await service.update_allocation_quantity(
        request.state.user.id, event_id, allocation_id, body.quantity
    )
    return BaseResponse(data=DayTicketAllocationResponse.model_validate(allocation))

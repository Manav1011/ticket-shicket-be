from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependencies import get_current_user
from db.session import db_session
from utils.schema import BaseResponse

from .repository import ResellerRepository
from .response import ResellerEventsResponse, ResellerTicketsResponse, ResellerAllocationsResponse
from .service import ResellerService
from apps.resellers.request import CreateResellerCustomerTransferRequest
from apps.organizer.response import CustomerTransferResponse

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


@router.get("/b2b/events/{event_id}/tickets")
async def get_my_reseller_tickets(
    event_id: UUID,
    request: Request,
    service: Annotated[ResellerService, Depends(get_reseller_service)],
    event_day_id: UUID | None = None,
) -> ResellerTicketsResponse:
    """Get my tickets for an event I resell."""
    return await service.get_my_tickets(event_id, request.state.user.id, event_day_id=event_day_id)


@router.get("/b2b/events/{event_id}/my-allocations")
async def get_my_reseller_allocations(
    event_id: UUID,
    request: Request,
    service: Annotated[ResellerService, Depends(get_reseller_service)],
    limit: int = 50,
    offset: int = 0,
) -> ResellerAllocationsResponse:
    """Get my allocations for an event I resell."""
    return await service.get_my_allocations(event_id, request.state.user.id, limit, offset)


@router.post("/b2b/events/{event_id}/transfers/customer")
async def create_reseller_customer_transfer_endpoint(
    event_id: UUID,
    request: Request,
    body: Annotated[CreateResellerCustomerTransferRequest, Body()],
    service: Annotated[ResellerService, Depends(get_reseller_service)],
) -> BaseResponse[CustomerTransferResponse]:
    """
    [Reseller] Transfer B2B tickets to a customer via phone or email.
    Free mode: immediately transfers ticket ownership and generates a claim link.
    Paid mode: returns not_implemented stub.
    """
    result = await service.create_reseller_customer_transfer(
        user_id=request.state.user.id,
        event_id=event_id,
        phone=body.phone,
        email=body.email,
        quantity=body.quantity,
        event_day_id=body.event_day_id,
        mode=body.mode,
        price=body.price,
    )
    return BaseResponse(data=result)

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, File, UploadFile, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from apps.event.response import EventSummaryResponse, EventResponse
from auth.dependencies import get_current_user
from db.session import db_session
from utils.schema import BaseResponse

from .repository import OrganizerRepository
from .request import CreateOrganizerPageRequest, UpdateOrganizerPageRequest, CreateB2BRequestBody, ConfirmB2BPaymentBody, CreateB2BTransferRequest
from .response import OrganizerPageResponse, MyB2BTicketsResponse, MyB2BAllocationItem, B2BTransferResponse
from .service import OrganizerService
from apps.superadmin.response import B2BRequestResponse

router = APIRouter(
    prefix="/api/organizers", tags=["Organizer"], dependencies=[Depends(get_current_user)]
)


def get_organizer_service(
    session: Annotated[AsyncSession, Depends(db_session)],
) -> OrganizerService:
    return OrganizerService(OrganizerRepository(session))


@router.get("")
async def list_organizers(
    request: Request,
    service: Annotated[OrganizerService, Depends(get_organizer_service)],
) -> BaseResponse[list[OrganizerPageResponse]]:
    organizers = await service.list_organizers(request.state.user.id)
    return BaseResponse(data=[OrganizerPageResponse.model_validate(item) for item in organizers])


@router.post("")
async def create_organizer(
    request: Request,
    body: Annotated[CreateOrganizerPageRequest, Body()],
    service: Annotated[OrganizerService, Depends(get_organizer_service)],
) -> BaseResponse[OrganizerPageResponse]:
    organizer = await service.create_organizer(
        owner_user_id=request.state.user.id,
        **body.model_dump(),
    )
    return BaseResponse(data=OrganizerPageResponse.model_validate(organizer))


@router.patch("/{organizer_id}")
async def update_organizer(
    organizer_id: UUID,
    request: Request,
    body: Annotated[UpdateOrganizerPageRequest, Body()],
    service: Annotated[OrganizerService, Depends(get_organizer_service)],
) -> BaseResponse[OrganizerPageResponse]:
    organizer = await service.update_organizer(
        request.state.user.id,
        organizer_id,
        **body.model_dump(exclude_unset=True),
    )
    return BaseResponse(data=OrganizerPageResponse.model_validate(organizer))


@router.get("/{organizer_id}/events")
async def list_organizer_events(
    organizer_id: UUID,
    request: Request,
    service: Annotated[OrganizerService, Depends(get_organizer_service)],
    status: str | None = None,
) -> BaseResponse[list[EventSummaryResponse]]:
    events = await service.list_organizer_events(request.state.user.id, organizer_id, status)
    return BaseResponse(data=[EventSummaryResponse.model_validate(item) for item in events])


@router.get("/events")
async def list_my_events(
    request: Request,
    service: Annotated[OrganizerService, Depends(get_organizer_service)],
    status: str | None = None,
    event_access_type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    search: str | None = None,
    sort_by: str = "created_at",
    order: str = "desc",
    limit: int = 20,
    offset: int = 0,
) -> BaseResponse[dict]:
    """
    [Organizer] List all events across all organizer pages owned by the current user.
    Supports filtering by status, event_access_type, date range, and title search.
    Sortable by created_at, start_date, title, status. Paginated with limit/offset.
    """
    events, pagination_meta = await service.list_my_events(
        user_id=request.state.user.id,
        status=status,
        event_access_type=event_access_type,
        date_from=date_from,
        date_to=date_to,
        search=search,
        sort_by=sort_by,
        order=order,
        limit=limit,
        offset=offset,
    )

    return BaseResponse(data={
        "events": [EventResponse.model_validate(e) for e in events],
        "pagination": pagination_meta,
    })


@router.post("/{organizer_id}/logo")
async def upload_organizer_logo(
    organizer_id: UUID,
    request: Request,
    file: Annotated[UploadFile, File(...)],
    service: Annotated[OrganizerService, Depends(get_organizer_service)],
):
    """Upload logo image for organizer page."""
    from src.utils.file_validation import FileValidationError
    from fastapi import HTTPException

    try:
        file_content = await file.read()
        organizer = await service.upload_logo(
            owner_user_id=request.state.user.id,
            organizer_page_id=organizer_id,
            file_name=file.filename,
            file_content=file_content,
        )
        return BaseResponse(data=OrganizerPageResponse.model_validate(organizer))
    except FileValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{organizer_id}/cover")
async def upload_organizer_cover(
    organizer_id: UUID,
    request: Request,
    file: Annotated[UploadFile, File(...)],
    service: Annotated[OrganizerService, Depends(get_organizer_service)],
):
    """Upload cover image for organizer page."""
    from src.utils.file_validation import FileValidationError
    from fastapi import HTTPException

    try:
        file_content = await file.read()
        organizer = await service.upload_cover_image(
            owner_user_id=request.state.user.id,
            organizer_page_id=organizer_id,
            file_name=file.filename,
            file_content=file_content,
        )
        return BaseResponse(data=OrganizerPageResponse.model_validate(organizer))
    except FileValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- B2B Request Endpoints ---

@router.post("/b2b/events/{event_id}/requests")
async def create_b2b_request(
    event_id: UUID,
    request: Request,
    body: Annotated[CreateB2BRequestBody, Body()],
    service: Annotated[OrganizerService, Depends(get_organizer_service)],
) -> BaseResponse[B2BRequestResponse]:
    """
    [Organizer] Submit a B2B ticket request.
    Organizer provides event and day only — system auto-derives B2B ticket type.
    """
    from apps.event.repository import EventRepository

    event_repo = EventRepository(service.repository.session)

    # Validate event_day belongs to event
    event_day = await event_repo.get_event_day_by_id(UUID(body.event_day_id))
    if not event_day or event_day.event_id != UUID(body.event_id):
        raise HTTPException(status_code=400, detail="event_day_id does not belong to event_id")

    # Verify user owns the organizer page that owns this event
    event = await event_repo.get_by_id(UUID(body.event_id))
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    organizer = await service.repository.get_by_id_for_owner(event.organizer_page_id, request.state.user.id)
    if not organizer:
        raise HTTPException(status_code=403, detail="You do not own this event's organizer page")

    b2b_req = await service.create_b2b_request(
        user_id=request.state.user.id,
        event_id=UUID(body.event_id),
        event_day_id=UUID(body.event_day_id),
        quantity=body.quantity,
    )
    return BaseResponse(data=B2BRequestResponse.model_validate(b2b_req))


@router.get("/b2b/events/{event_id}/requests")
async def list_b2b_requests_for_event(
    event_id: UUID,
    request: Request,
    service: Annotated[OrganizerService, Depends(get_organizer_service)],
) -> BaseResponse[list[B2BRequestResponse]]:
    """
    [Organizer] List B2B requests for a specific event.
    User must own the organizer page that owns the event.
    """
    from apps.event.repository import EventRepository

    event_repo = EventRepository(service.repository.session)

    # Verify user owns the organizer page that owns this event
    event = await event_repo.get_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    organizer = await service.repository.get_by_id_for_owner(event.organizer_page_id, request.state.user.id)
    if not organizer:
        raise HTTPException(status_code=403, detail="You do not own this event's organizer page")

    requests = await service.get_b2b_requests_for_event(event_id)
    return BaseResponse(data=[B2BRequestResponse.model_validate(r) for r in requests])


@router.post("/b2b/events/{event_id}/requests/{b2b_request_id}/confirm-payment")
async def confirm_b2b_payment(
    event_id: UUID,
    b2b_request_id: UUID,
    request: Request,
    service: Annotated[OrganizerService, Depends(get_organizer_service)],
    body: Annotated[ConfirmB2BPaymentBody, Body()],
) -> BaseResponse[B2BRequestResponse]:
    """
    [Organizer] Confirm payment for an approved paid B2B request.
    Mock payment success — triggers allocation creation.
    User must own the organizer page that owns the event.
    """
    b2b_req = await service.confirm_b2b_payment(
        request_id=b2b_request_id,
        event_id=event_id,
        user_id=request.state.user.id,
    )
    return BaseResponse(data=B2BRequestResponse.model_validate(b2b_req))


@router.post("/b2b/events/{event_id}/transfers/reseller")
async def create_b2b_transfer_endpoint(
    event_id: UUID,
    request: Request,
    body: Annotated[CreateB2BTransferRequest, Body()],
    service: Annotated[OrganizerService, Depends(get_organizer_service)],
) -> BaseResponse[B2BTransferResponse]:
    """
    [Organizer] Transfer B2B tickets to a reseller.
    Free mode: immediately transfers ticket ownership.
    Paid mode: returns not_implemented stub.
    """
    result = await service.create_b2b_transfer(
        user_id=request.state.user.id,
        event_id=event_id,
        reseller_id=body.reseller_id,
        quantity=body.quantity,
        event_day_id=body.event_day_id,
        mode=body.mode,
    )
    return BaseResponse(data=result)


@router.get("/b2b/events/{event_id}/my-tickets")
async def get_my_b2b_tickets(
    event_id: UUID,
    request: Request,
    service: Annotated[OrganizerService, Depends(get_organizer_service)],
    event_day_id: UUID | None = None,
) -> BaseResponse[MyB2BTicketsResponse]:
    """
    [Organizer] Get B2B tickets owned by the organizer for an event.
    Grouped by event day and ticket type.
    """
    result = await service.get_my_b2b_tickets(event_id, request.state.user.id, event_day_id=event_day_id)
    return BaseResponse(data=MyB2BTicketsResponse(**result))


@router.get("/b2b/events/{event_id}/my-allocations")
async def get_my_b2b_allocations(
    event_id: UUID,
    request: Request,
    service: Annotated[OrganizerService, Depends(get_organizer_service)],
    event_day_id: UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> BaseResponse[list[MyB2BAllocationItem]]:
    """
    [Organizer] Get B2B allocation history (received AND transferred)
    for tickets owned by the organizer.
    """
    allocations = await service.get_my_b2b_allocations(
        event_id, request.state.user.id, event_day_id=event_day_id, limit=limit, offset=offset
    )
    return BaseResponse(data=[MyB2BAllocationItem(**a) for a in allocations])

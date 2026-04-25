from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Request, File, UploadFile, Form
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependencies import get_current_user
from db.session import db_session
from utils.schema import BaseResponse

from apps.organizer.repository import OrganizerRepository
from apps.ticketing.repository import TicketingRepository
from .repository import EventRepository
from .request import CreateDraftEventRequest, CreateEventDayRequest, UpdateEventBasicInfoRequest, UpdateEventDayRequest, UpdateMediaAssetMetadataRequest, UpdateShowTicketsRequest, CreateResellerInviteRequest
from .response import EventDayResponse, EventReadinessResponse, EventResponse, PublishValidationResponse, ScanStatusHistoryResponse, MediaAssetResponse, ResellerResponse, ResellerInviteResponse
from .service import EventService

from apps.user.invite.service import InviteService as UserInviteService
from apps.user.invite.repository import InviteRepository as UserInviteRepository
from apps.user.invite.request import CreateInviteRequest
from apps.user.invite.response import InviteResponse
from apps.user.repository import UserRepository

router = APIRouter(prefix="/api/events", tags=["Event"], dependencies=[Depends(get_current_user)])


def get_event_service(
    session: Annotated[AsyncSession, Depends(db_session)],
) -> EventService:
    return EventService(EventRepository(session), OrganizerRepository(session), TicketingRepository(session))


def get_user_invite_service(
    session: Annotated[AsyncSession, Depends(db_session)],
) -> UserInviteService:
    return UserInviteService(
        repository=UserInviteRepository(session),
        user_repository=UserRepository(session),
    )


@router.post("/drafts")
async def create_draft_event(
    request: Request,
    body: Annotated[CreateDraftEventRequest, Body()],
    service: Annotated[EventService, Depends(get_event_service)],
) -> BaseResponse[EventResponse]:
    event = await service.create_draft_event(
        request.state.user.id,
        body.organizer_page_id,
        body.title,
        body.event_access_type,
    )
    return BaseResponse(data=EventResponse.model_validate(event))


@router.get("/{event_id}")
async def get_event_detail(
    event_id: UUID,
    request: Request,
    service: Annotated[EventService, Depends(get_event_service)],
) -> BaseResponse[EventResponse]:
    event = await service.get_event_detail(request.state.user.id, event_id)
    return BaseResponse(data=EventResponse.model_validate(event))


@router.patch("/{event_id}/basic-info")
async def update_basic_info(
    event_id: UUID,
    request: Request,
    body: Annotated[UpdateEventBasicInfoRequest, Body()],
    service: Annotated[EventService, Depends(get_event_service)],
) -> BaseResponse[EventResponse]:
    event = await service.update_basic_info(
        request.state.user.id,
        event_id,
        **body.model_dump(exclude_unset=True),
    )
    return BaseResponse(data=EventResponse.model_validate(event))


@router.patch("/{event_id}/show-tickets")
async def update_show_tickets(
    event_id: UUID,
    request: Request,
    body: Annotated[UpdateShowTicketsRequest, Body()],
    service: Annotated[EventService, Depends(get_event_service)],
) -> BaseResponse[EventResponse]:
    event = await service.update_show_tickets(
        request.state.user.id,
        event_id,
        **body.model_dump(exclude_unset=True),
    )
    return BaseResponse(data=EventResponse.model_validate(event))


@router.get("/{event_id}/readiness")
async def get_event_readiness(
    event_id: UUID,
    request: Request,
    service: Annotated[EventService, Depends(get_event_service)],
) -> BaseResponse[EventReadinessResponse]:
    readiness = await service.get_readiness(request.state.user.id, event_id)
    return BaseResponse(data=EventReadinessResponse.model_validate(readiness))


@router.get("/{event_id}/publish-validations")
async def get_publish_validations(
    event_id: UUID,
    request: Request,
    service: Annotated[EventService, Depends(get_event_service)],
) -> BaseResponse[PublishValidationResponse]:
    """Check if event is ready to publish, return section-by-section validation errors."""
    validation = await service.validate_for_publish(request.state.user.id, event_id)
    return BaseResponse(data=PublishValidationResponse.model_validate(validation))


@router.post("/{event_id}/publish")
async def publish_event(
    event_id: UUID,
    request: Request,
    service: Annotated[EventService, Depends(get_event_service)],
) -> BaseResponse[EventResponse]:
    """Publish event. Returns 400 with validation errors if not ready."""
    event = await service.publish_event(request.state.user.id, event_id)
    return BaseResponse(data=EventResponse.model_validate(event))


@router.post("/{event_id}/days")
async def create_event_day(
    event_id: UUID,
    request: Request,
    body: Annotated[CreateEventDayRequest, Body()],
    service: Annotated[EventService, Depends(get_event_service)],
) -> BaseResponse[EventDayResponse]:
    day = await service.create_event_day(
        request.state.user.id,
        event_id,
        body.date,
        start_time=body.start_time,
        end_time=body.end_time,
    )
    return BaseResponse(data=EventDayResponse.model_validate(day))


@router.get("/{event_id}/days")
async def list_event_days(
    event_id: UUID,
    request: Request,
    service: Annotated[EventService, Depends(get_event_service)],
) -> BaseResponse[list[EventDayResponse]]:
    days = await service.list_event_days(request.state.user.id, event_id)
    return BaseResponse(data=[EventDayResponse.model_validate(item) for item in days])


@router.patch("/days/{event_day_id}")
async def update_event_day(
    event_day_id: UUID,
    request: Request,
    body: Annotated[UpdateEventDayRequest, Body()],
    service: Annotated[EventService, Depends(get_event_service)],
) -> BaseResponse[EventDayResponse]:
    day = await service.update_event_day(
        request.state.user.id,
        event_day_id,
        **body.model_dump(exclude_unset=True),
    )
    return BaseResponse(data=EventDayResponse.model_validate(day))


@router.delete("/days/{event_day_id}")
async def delete_event_day(
    event_day_id: UUID,
    request: Request,
    service: Annotated[EventService, Depends(get_event_service)],
) -> BaseResponse[dict]:
    await service.delete_event_day(request.state.user.id, event_day_id)
    return BaseResponse(data={"deleted": True})


@router.post("/days/{event_day_id}/start-scan")
async def start_scan(
    event_day_id: UUID,
    request: Request,
    service: Annotated[EventService, Depends(get_event_service)],
) -> BaseResponse[EventDayResponse]:
    day = await service.start_scan(request.state.user.id, event_day_id)
    return BaseResponse(data=EventDayResponse.model_validate(day))


@router.post("/days/{event_day_id}/pause-scan")
async def pause_scan(
    event_day_id: UUID,
    request: Request,
    service: Annotated[EventService, Depends(get_event_service)],
) -> BaseResponse[EventDayResponse]:
    day = await service.pause_scan(request.state.user.id, event_day_id)
    return BaseResponse(data=EventDayResponse.model_validate(day))


@router.post("/days/{event_day_id}/resume-scan")
async def resume_scan(
    event_day_id: UUID,
    request: Request,
    service: Annotated[EventService, Depends(get_event_service)],
) -> BaseResponse[EventDayResponse]:
    day = await service.resume_scan(request.state.user.id, event_day_id)
    return BaseResponse(data=EventDayResponse.model_validate(day))


@router.post("/days/{event_day_id}/end-scan")
async def end_scan(
    event_day_id: UUID,
    request: Request,
    service: Annotated[EventService, Depends(get_event_service)],
) -> BaseResponse[EventDayResponse]:
    day = await service.end_scan(request.state.user.id, event_day_id)
    return BaseResponse(data=EventDayResponse.model_validate(day))


@router.get("/days/{event_day_id}/scan-history")
async def get_scan_status_history(
    event_day_id: UUID,
    request: Request,
    service: Annotated[EventService, Depends(get_event_service)],
) -> BaseResponse[list[ScanStatusHistoryResponse]]:
    day = await service.repository.get_event_day_for_owner(event_day_id, request.state.user.id)
    if not day:
        from .exceptions import EventNotFound
        raise EventNotFound
    history = await service.repository.list_scan_status_history(event_day_id)
    return BaseResponse(
        data=[
            ScanStatusHistoryResponse.model_validate(h) for h in history
        ]
    )


@router.post("/{event_id}/media-assets", response_model=BaseResponse[MediaAssetResponse])
async def upload_media_asset(
    request: Request,
    event_id: UUID,
    asset_type: Annotated[str, Form(...)],
    file: Annotated[UploadFile, File(...)],
    service: Annotated[EventService, Depends(get_event_service)],
    title: Annotated[str | None, Form()] = None,
    caption: Annotated[str | None, Form()] = None,
    alt_text: Annotated[str | None, Form()] = None,
):
    """Upload media asset to event."""
    from .exceptions import InvalidAsset
    from src.utils.file_validation import FileValidationError

    try:
        file_content = await file.read()
        asset = await service.upload_media_asset(
            owner_user_id=request.state.user.id,
            event_id=event_id,
            asset_type=asset_type,
            file_name=file.filename,
            file_content=file_content,
            title=title,
            caption=caption,
            alt_text=alt_text,
        )
        return BaseResponse(data=MediaAssetResponse.model_validate(asset))
    except FileValidationError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{event_id}/media-assets", response_model=BaseResponse[list[MediaAssetResponse]])
async def list_media_assets(
    request: Request,
    event_id: UUID,
    service: Annotated[EventService, Depends(get_event_service)],
    asset_type: str | None = None,
):
    """List media assets for event."""
    assets = await service.list_media_assets(
        owner_user_id=request.state.user.id,
        event_id=event_id,
        asset_type=asset_type,
    )
    return BaseResponse(data=[MediaAssetResponse.model_validate(a) for a in assets])


@router.delete("/{event_id}/media-assets/{asset_id}", response_model=BaseResponse[dict])
async def delete_media_asset(
    request: Request,
    event_id: UUID,
    asset_id: UUID,
    service: Annotated[EventService, Depends(get_event_service)],
):
    """Delete media asset from event."""
    await service.delete_media_asset(
        owner_user_id=request.state.user.id,
        event_id=event_id,
        asset_id=asset_id,
    )
    return BaseResponse(data={"message": "Asset deleted"})


@router.patch("/{event_id}/media-assets/{asset_id}", response_model=BaseResponse[MediaAssetResponse])
async def update_media_asset_metadata(
    request: Request,
    event_id: UUID,
    asset_id: UUID,
    body: Annotated[UpdateMediaAssetMetadataRequest, Body()],
    service: Annotated[EventService, Depends(get_event_service)],
):
    """Update media asset metadata."""
    asset = await service.update_media_asset_metadata(
        owner_user_id=request.state.user.id,
        event_id=event_id,
        asset_id=asset_id,
        title=body.title,
        caption=body.caption,
        alt_text=body.alt_text,
        sort_order=body.sort_order,
        is_primary=body.is_primary,
    )
    return BaseResponse(data=MediaAssetResponse.model_validate(asset))


@router.post("/{event_id}/reseller-invites")
async def create_reseller_invite(
    event_id: UUID,
    request: Request,
    body: Annotated[CreateResellerInviteRequest, Body()],
    event_service: Annotated[EventService, Depends(get_event_service)],
    invite_service: Annotated[UserInviteService, Depends(get_user_invite_service)],
) -> BaseResponse[list[ResellerInviteResponse]]:
    # Verify organizer owns event
    event = await event_service.repository.get_by_id_for_owner(event_id, request.state.user.id)
    if not event:
        from apps.event.exceptions import OrganizerOwnershipError
        raise OrganizerOwnershipError

    # Validate all users exist first (fail fast before any inserts)
    for user_id in body.user_ids:
        target_user = await invite_service.user_repository.find_by_id(user_id)
        if not target_user:
            from exceptions import NotFoundError
            raise NotFoundError(f"User {user_id} not found")
        if target_user.id == request.state.user.id:
            from exceptions import ForbiddenError
            raise ForbiddenError("Cannot invite yourself as a reseller")
        # Check for duplicate pending invite
        existing = await invite_service.repository.get_pending_invite_for_user_event(
            target_user_id=user_id,
            event_id=event_id,
        )
        if existing:
            from exceptions import AlreadyExistsError
            raise AlreadyExistsError(f"Pending invite already exists for user {user_id}")

    # Batch create all invites in ONE DB call
    meta = {"event_id": str(event_id), "permissions": body.permissions or []}
    from apps.user.invite.enums import InviteType
    created_invites = await invite_service.create_invite_batch(
        target_user_ids=body.user_ids,
        created_by_id=request.state.user.id,
        metadata=meta,
        invite_type=InviteType.reseller.value,
    )

    return BaseResponse(data=[ResellerInviteResponse.model_validate(i) for i in created_invites])


@router.get("/{event_id}/reseller-invites")
async def list_event_reseller_invites(
    event_id: UUID,
    request: Request,
    event_service: Annotated[EventService, Depends(get_event_service)],
    status: str | None = None,  # pending, accepted, declined, cancelled
) -> BaseResponse[list[ResellerInviteResponse]]:
    # Verify organizer owns event
    event = await event_service.repository.get_by_id_for_owner(event_id, request.state.user.id)
    if not event:
        from apps.event.exceptions import OrganizerOwnershipError
        raise OrganizerOwnershipError

    invites = await event_service.repository.list_reseller_invites_for_event(
        event_id=event_id,
        status=status,
    )
    return BaseResponse(data=[ResellerInviteResponse.model_validate(i) for i in invites])


@router.get("/{event_id}/resellers")
async def list_event_resellers(
    event_id: UUID,
    request: Request,
    event_service: Annotated[EventService, Depends(get_event_service)],
) -> BaseResponse[list[ResellerResponse]]:
    # Verify organizer owns event
    event = await event_service.repository.get_by_id_for_owner(event_id, request.state.user.id)
    if not event:
        from apps.event.exceptions import OrganizerOwnershipError
        raise OrganizerOwnershipError

    resellers = await event_service.repository.list_resellers_for_event(event_id)
    return BaseResponse(data=[ResellerResponse.model_validate(r) for r in resellers])

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, File, UploadFile, Request
from sqlalchemy.ext.asyncio import AsyncSession

from apps.event.response import EventSummaryResponse
from auth.dependencies import get_current_user
from db.session import db_session
from utils.schema import BaseResponse

from .repository import OrganizerRepository
from .request import CreateOrganizerPageRequest, UpdateOrganizerPageRequest
from .response import OrganizerPageResponse
from .service import OrganizerService

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

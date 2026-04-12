from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from apps.event.response import EventSummaryResponse
from db.session import db_session
from utils.schema import BaseResponse

from .public_service import PublicOrganizerService
from .repository import OrganizerRepository
from .response import OrganizerPageResponse


router = APIRouter(prefix="/api/open/organizers", tags=["Public Organizers"])


def get_public_organizer_service(
    session: Annotated[AsyncSession, Depends(db_session)],
) -> PublicOrganizerService:
    return PublicOrganizerService(OrganizerRepository(session))


@router.get("")
async def list_public_organizers(
    service: Annotated[PublicOrganizerService, Depends(get_public_organizer_service)],
) -> BaseResponse[list[OrganizerPageResponse]]:
    organizers = await service.list_organizers()
    return BaseResponse(
        data=[OrganizerPageResponse.model_validate(o) for o in organizers]
    )


@router.get("/{organizer_page_id}")
async def get_public_organizer(
    organizer_page_id: UUID,
    service: Annotated[PublicOrganizerService, Depends(get_public_organizer_service)],
) -> BaseResponse[OrganizerPageResponse]:
    organizer = await service.get_organizer(organizer_page_id)
    return BaseResponse(data=OrganizerPageResponse.model_validate(organizer))


@router.get("/{organizer_page_id}/events")
async def list_organizer_public_events(
    organizer_page_id: UUID,
    service: Annotated[PublicOrganizerService, Depends(get_public_organizer_service)],
) -> BaseResponse[list[EventSummaryResponse]]:
    events = await service.list_events_by_organizer(organizer_page_id)
    return BaseResponse(data=[EventSummaryResponse.model_validate(e) for e in events])

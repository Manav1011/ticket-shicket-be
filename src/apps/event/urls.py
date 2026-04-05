from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependencies import get_current_user
from db.session import db_session
from utils.schema import BaseResponse

from apps.organizer.repository import OrganizerRepository
from .repository import EventRepository
from .request import CreateDraftEventRequest
from .response import EventDayResponse, EventResponse
from .service import EventService

router = APIRouter(prefix="/api/events", tags=["Event"], dependencies=[Depends(get_current_user)])


def get_event_service(
    session: Annotated[AsyncSession, Depends(db_session)],
) -> EventService:
    return EventService(EventRepository(session), OrganizerRepository(session))


@router.post("/drafts")
async def create_draft_event(
    request: Request,
    body: Annotated[CreateDraftEventRequest, Body()],
    service: Annotated[EventService, Depends(get_event_service)],
) -> BaseResponse[EventResponse]:
    event = await service.create_draft_event(request.state.user.id, body.organizer_page_id)
    return BaseResponse(data=EventResponse.model_validate(event))


@router.post("/days/{event_day_id}/start-scan")
async def start_scan(
    event_day_id: UUID,
    request: Request,
    service: Annotated[EventService, Depends(get_event_service)],
) -> BaseResponse[EventDayResponse]:
    day = await service.start_scan(request.state.user.id, event_day_id)
    return BaseResponse(data=EventDayResponse.model_validate(day))

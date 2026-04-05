from typing import Annotated
from fastapi import APIRouter, Body, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependencies import get_current_user
from db.session import db_session
from utils.schema import BaseResponse

from .repository import OrganizerRepository
from .request import CreateOrganizerPageRequest
from .response import OrganizerPageResponse
from .service import OrganizerService

router = APIRouter(
    prefix="/api/organizers", tags=["Organizer"], dependencies=[Depends(get_current_user)]
)


def get_organizer_service(
    session: Annotated[AsyncSession, Depends(db_session)],
) -> OrganizerService:
    return OrganizerService(OrganizerRepository(session))


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

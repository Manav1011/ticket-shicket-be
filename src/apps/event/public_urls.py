from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi_limiter.depends import RateLimiter
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependencies import get_current_user_or_guest
from db.session import db_session
from src.constants.config import rate_limiter_config
from utils.schema import BaseResponse

from apps.organizer.repository import OrganizerRepository
from apps.ticketing.repository import TicketingRepository
from .repository import EventRepository
from .response import EventInterestResponse, EventSummaryResponse, EventDetailResponse
from .service import EventService
from .public_service import PublicEventService
from .claim_service import ClaimService

router = APIRouter(
    prefix="/api/open/events",
    tags=["Public Events"],
    # No router-level auth — GET routes are fully public
    # Auth is applied only at the route level for POST /interest
)


def get_event_service(session: Annotated[AsyncSession, Depends(db_session)]) -> EventService:
    return EventService(EventRepository(session), OrganizerRepository(session))


def get_public_event_service(session: Annotated[AsyncSession, Depends(db_session)]) -> PublicEventService:
    return PublicEventService(
        event_repository=EventRepository(session),
        ticketing_repository=TicketingRepository(session),
    )


@router.post(
    "/{event_id}/interest",
    dependencies=[
        Depends(get_current_user_or_guest),
        Depends(
            RateLimiter(
                times=rate_limiter_config["request_limit"],
                seconds=rate_limiter_config["time"],
            )
        ),
    ],
)
async def mark_event_interest(
    event_id: UUID,
    request: Request,
    service: Annotated[EventService, Depends(get_event_service)],
) -> BaseResponse[EventInterestResponse]:
    actor = request.state.actor
    result = await service.interest_event(
        actor_kind=actor.kind,
        actor_id=actor.id,
        event_id=event_id,
        ip_address=request.client.host if request.client else "unknown",
        user_agent=request.headers.get("user-agent"),
    )
    return BaseResponse(data=EventInterestResponse.model_validate(result))


# ── Event List ──────────────────────────────────────────────────────────────

@router.get("")
async def list_public_events(
    service: Annotated[PublicEventService, Depends(get_public_event_service)],
) -> BaseResponse[list[EventSummaryResponse]]:
    events = await service.list_public_events()
    return BaseResponse(data=[EventSummaryResponse.model_validate(e) for e in events])


# ── Event Detail ───────────────────────────────────────────────────────────

@router.get("/{event_id}")
async def get_public_event(
    event_id: UUID,
    service: Annotated[PublicEventService, Depends(get_public_event_service)],
) -> BaseResponse[EventDetailResponse]:
    event = await service.get_public_event(event_id)
    return BaseResponse(data=EventDetailResponse.model_validate(event))


# ── Claim Link Redemption ───────────────────────────────────────────────────

claim_router = APIRouter(
    prefix="/api/open/claim",
    tags=["Claim Link"],
)


def get_claim_service(
    session: Annotated[AsyncSession, Depends(db_session)],
) -> ClaimService:
    return ClaimService(session)


@claim_router.get("/{token}", operation_id="redeem_claim_link")
async def redeem_claim_link(
    token: str,
    service: Annotated[ClaimService, Depends(get_claim_service)],
) -> str:
    """
    [PUBLIC — No Auth Required]

    Redeem a claim link token and receive a scan JWT.
    The JWT contains the customer's ticket indexes for a specific event day.

    Returns:
        Plain JWT string (not a JSON object)
    """
    jwt = await service.get_jwt_for_claim_token(token)
    return jwt

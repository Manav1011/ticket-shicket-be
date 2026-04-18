from datetime import datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, Request, Security, status
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

import constants
from .models import UserModel
from .request import SignInRequest, SignUpRequest, GetUserByIdRequest, DeleteUserByIdRequest, UserLookupRequest
from .response import BaseUserResponse, UserLookupResponse
from .service import UserService
from .repository import UserRepository
from auth.dependencies import get_current_user
from auth.schemas import RefreshRequest, TokenPair, RefreshRequestWithJti
from auth.blocklist import TokenBlocklist
from db.session import db_session
from db.redis import redis
from utils.schema import BaseResponse
from utils.cookies import set_auth_cookies
from config import settings

from apps.user.invite.service import InviteService as UserInviteService
from apps.user.invite.repository import InviteRepository as UserInviteRepository
from apps.user.invite.response import InviteResponse
from apps.event.response import ResellerResponse
from apps.event.exceptions import EventNotFound

router = APIRouter(prefix="/api/user", tags=["User"])
protected_router = APIRouter(prefix="/api/user", tags=["User"], dependencies=[Depends(get_current_user)])


def get_user_service(session: Annotated[AsyncSession, Depends(db_session)]) -> UserService:
    return UserService(
        UserRepository(session),
        TokenBlocklist(redis=redis),
    )


def get_user_invite_service(session: Annotated[AsyncSession, Depends(db_session)]) -> UserInviteService:
    return UserInviteService(
        repository=UserInviteRepository(session),
        user_repository=UserRepository(session),
    )


def get_event_service(session: Annotated[AsyncSession, Depends(db_session)]):
    # Lazy imports to avoid circular import issues
    from apps.organizer.repository import OrganizerRepository
    from apps.event.repository import EventRepository
    from apps.event.service import EventService
    
    return EventService(EventRepository(session), OrganizerRepository(session))


# ==================== PROTECTED USER ROUTES ====================


@protected_router.get("/me/invites")
async def list_pending_invites(
    request: Request,
    service: Annotated[UserInviteService, Depends(get_user_invite_service)],
) -> BaseResponse[list[InviteResponse]]:
    invites = await service.list_pending_invites_for_user(request.state.user.id)
    return BaseResponse(data=[InviteResponse.model_validate(i) for i in invites])


@protected_router.post("/invites/{invite_id}/accept")
async def accept_user_invite(
    invite_id: UUID,
    request: Request,
    invite_service: Annotated[UserInviteService, Depends(get_user_invite_service)],
    event_service: Annotated[dict, Depends(get_event_service)],
) -> BaseResponse[ResellerResponse]:
    """
    Accept a pending invite (reseller invite).
    Creates EventReseller record if event exists.
    """
    result = await invite_service.accept_invite(request.state.user.id, invite_id)

    event_id_str = result["event_id"]
    if not event_id_str:
        from apps.user.invite.exceptions import InviteNotFound
        raise InviteNotFound("Invite missing event_id in metadata")

    event_id = UUID(event_id_str)

    # Check if event exists
    event = await event_service.repository.get_by_id(event_id)
    if not event:
        raise EventNotFound("Event not found")

    # Check if reseller already exists (idempotent — return existing)
    existing = await event_service.repository.get_reseller_for_event(
        request.state.user.id, event_id
    )
    if existing:
        return BaseResponse(data=ResellerResponse.model_validate(existing))

    permissions = result["permissions"]

    reseller = await event_service.repository.create_event_reseller(
        user_id=request.state.user.id,
        event_id=event_id,
        invited_by_id=result["invite"].created_by_id,
        permissions=permissions,
    )
    return BaseResponse(data=ResellerResponse.model_validate(reseller))


@protected_router.post("/invites/{invite_id}/decline")
async def decline_user_invite(
    invite_id: UUID,
    request: Request,
    invite_service: Annotated[UserInviteService, Depends(get_user_invite_service)],
) -> BaseResponse[dict]:
    """Decline a pending invite."""
    await invite_service.decline_invite(request.state.user.id, invite_id)
    return BaseResponse(data={"declined": True})


@protected_router.delete("/invites/{invite_id}")
async def cancel_user_invite(
    invite_id: UUID,
    request: Request,
    invite_service: Annotated[UserInviteService, Depends(get_user_invite_service)],
) -> BaseResponse[dict]:
    """Cancel a pending invite (only the invite creator can cancel)."""
    await invite_service.cancel_invite(request.state.user.id, invite_id)
    return BaseResponse(data={"cancelled": True})


# ==================== PUBLIC ROUTES ====================

@router.post("/sign-in", status_code=status.HTTP_200_OK, operation_id="sign_in")
async def sign_in(
    body: Annotated[SignInRequest, Body()],
    service: Annotated[UserService, Depends(get_user_service)],
) -> JSONResponse:
    """
    Login endpoint. Validates credentials and issues tokens.
    Refresh token is stored in DB for rotation support.
    """
    tokens = await service.login_user(**body.model_dump())

    # Store refresh token in DB
    user = await service.repository.get_by_email(body.email)
    token_hash = service._hash_token(tokens["refresh_token"])
    await service.repository.create_refresh_token(
        token_hash=token_hash,
        user_id=user.id,
        expires_at=datetime.utcnow() + timedelta(seconds=int(settings.REFRESH_TOKEN_EXP)),
    )
    await service.repository.session.flush()

    data = {"status": constants.SUCCESS, "code": status.HTTP_200_OK, "data": tokens}
    response = JSONResponse(content=data)
    return set_auth_cookies(response, tokens)


@router.post("/refresh", status_code=status.HTTP_200_OK, operation_id="refresh")
async def refresh_token(
    body: RefreshRequest,
    service: Annotated[UserService, Depends(get_user_service)],
) -> TokenPair:
    """
    Refresh endpoint. Validates refresh token, rotates pair.
    Old refresh token is revoked, new access + refresh issued.
    """
    return await service.refresh_user(body.refresh_token)


@router.post("/create", status_code=status.HTTP_201_CREATED, operation_id="create_user")
async def create_user(
    body: Annotated[SignUpRequest, Body()],
    service: Annotated[UserService, Depends(get_user_service)],
) -> BaseResponse[BaseUserResponse]:
    user = await service.create_user(**body.model_dump())
    return BaseResponse(data=BaseUserResponse.model_validate(user))

@router.get("/find")
async def find_user_endpoint(
    email: str | None = None,
    phone: str | None = None,
    service: Annotated[UserService, Depends(get_user_service)] = None,
) -> BaseResponse[UserLookupResponse]:
    """Find user by email or phone. Returns user ID and basic info."""
    if not email and not phone:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="email or phone query parameter required")

    user = await service.find_user(email=email, phone=phone)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return BaseResponse(data=user)

# ==================== PROTECTED ROUTES ====================

@protected_router.post("/logout", status_code=status.HTTP_200_OK, operation_id="logout")
async def logout(
    request: Request,
    body: RefreshRequestWithJti,
    service: Annotated[UserService, Depends(get_user_service)],
):
    """Logout endpoint. Revokes refresh token and blocklists access token."""
    user: UserModel = request.state.user  # from auth dependency
    await service.logout_user(
        refresh_token=body.refresh_token,
        access_token_jti=body.access_token_jti,
    )
    return BaseResponse(message="Logged out successfully")


@protected_router.get("/self", status_code=status.HTTP_200_OK, operation_id="get_self")
async def get_self(
    request: Request,
    service: Annotated[UserService, Depends(get_user_service)],
) -> BaseResponse[BaseUserResponse]:
    user: UserModel = request.state.user
    return BaseResponse(data=BaseUserResponse.model_validate(await service.get_self(user_id=user.id)))


@protected_router.get("/", status_code=status.HTTP_200_OK, operation_id="get_user_by_id")
async def get_user_by_id(
    query: Annotated[GetUserByIdRequest, Query()],
    request: Request,
    service: Annotated[UserService, Depends(get_user_service)],
) -> BaseResponse[BaseUserResponse]:
    current_user: UserModel = request.state.user
    if query.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    user = await service.get_user_by_id(current_user.id)
    return BaseResponse(data=BaseUserResponse.model_validate(user))


@protected_router.delete("/", status_code=status.HTTP_200_OK, operation_id="delete_user_by_id")
async def delete_user_by_id(
    query: Annotated[DeleteUserByIdRequest, Query()],
    request: Request,
    service: Annotated[UserService, Depends(get_user_service)],
) -> BaseResponse[BaseUserResponse]:
    current_user: UserModel = request.state.user
    if query.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    deleted_user = await service.delete_user_by_id(current_user.id)
    return BaseResponse(data=BaseUserResponse.model_validate(deleted_user))

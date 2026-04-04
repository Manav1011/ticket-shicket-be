from typing import Annotated
import uuid
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Header, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependencies import get_current_guest
from auth.blocklist import TokenBlocklist
from .models import GuestModel
from .request import GuestConvertRequest, GuestLoginRequest
from .response import GuestLoginResponse, GuestResponse, GuestDeviceResponse
from .service import GuestService
from .repository import GuestRepository
from apps.user.repository import UserRepository
from db.session import db_session
from db.redis import redis
from auth.schemas import RefreshRequest, RefreshRequestWithJti, TokenPair
from utils.schema import BaseResponse
from utils.cookies import set_auth_cookies
from constants import SUCCESS
from config import settings


router = APIRouter(prefix="/api/guest", tags=["Guest"])
protected_router = APIRouter(
    prefix="/api/guest", tags=["Guest"], dependencies=[Depends(get_current_guest)]
)


def get_guest_service(session: Annotated[AsyncSession, Depends(db_session)]) -> GuestService:
    return GuestService(
        GuestRepository(session),
        UserRepository(session),
        TokenBlocklist(redis=redis),
    )


# PUBLIC ROUTES

@router.get("/device", status_code=status.HTTP_200_OK, operation_id="generate_device_id")
async def generate_device_id() -> BaseResponse[GuestDeviceResponse]:
    """
    Generate a new device ID (UUID) for a guest.
    Client stores this and sends it in X-Device-ID header on subsequent requests.
    """
    return BaseResponse(data=GuestDeviceResponse(device_id=uuid.uuid4()))


@router.post("/login", status_code=status.HTTP_200_OK, operation_id="guest_login")
async def guest_login(
    device_id_header: Annotated[str, Header(alias="X-Device-ID")],
    service: Annotated[GuestService, Depends(get_guest_service)],
) -> JSONResponse:
    """
    Login or register guest by device_id.
    Device ID is sent in X-Device-ID header (generated client-side).
    Server generates guest_id and returns tokens.
    """
    device_id = UUID(device_id_header)
    result = await service.login_guest(device_id)

    data = {"status": SUCCESS, "code": status.HTTP_200_OK, "data": result}
    response = JSONResponse(content=data)
    # Set cookies for web clients
    response = set_auth_cookies(
        response,
        {"access_token": result["access_token"], "refresh_token": result["refresh_token"]},
    )
    return response


@router.post("/refresh", status_code=status.HTTP_200_OK, operation_id="guest_refresh")
async def guest_refresh(
    body: RefreshRequest,
    service: Annotated[GuestService, Depends(get_guest_service)],
) -> TokenPair:
    """
    Refresh guest access token.
    Validates refresh token, rotates pair, revokes old, issues new.
    """
    return await service.refresh_guest(body.refresh_token)


# PROTECTED ROUTES (require valid guest token)

@protected_router.post(
    "/convert", status_code=status.HTTP_200_OK, operation_id="convert_guest_to_user"
)
async def convert_guest(
    request: Request,
    body: GuestConvertRequest,
    service: Annotated[GuestService, Depends(get_guest_service)],
) -> JSONResponse:
    """
    Convert guest to user at checkout.
    Requires valid guest token.
    Creates User record, links to Guest, returns new user tokens.
    """
    guest: GuestModel = request.state.guest

    result = await service.convert_guest(
        guest_id=guest.id,
        email=body.email,
        phone=body.phone,
        password=body.password,
        first_name=body.first_name,
        last_name=body.last_name,
    )

    data = {"status": SUCCESS, "code": status.HTTP_200_OK, "data": result}
    response = JSONResponse(content=data)
    response = set_auth_cookies(
        response,
        {"access_token": result["access_token"], "refresh_token": result["refresh_token"]},
    )
    return response


@protected_router.get("/self", status_code=status.HTTP_200_OK, operation_id="get_guest_self")
async def get_guest_self(
    request: Request,
    service: Annotated[GuestService, Depends(get_guest_service)],
) -> BaseResponse[GuestResponse]:
    """Get current guest info."""
    guest: GuestModel = request.state.guest
    return BaseResponse(data=GuestResponse(
        id=guest.id,
        device_id=guest.device_id,
        is_converted=guest.is_converted,
        converted_user_id=guest.converted_user_id,
    ))


@protected_router.post("/logout", status_code=status.HTTP_200_OK, operation_id="guest_logout")
async def guest_logout(
    request: Request,
    body: RefreshRequestWithJti,
    service: Annotated[GuestService, Depends(get_guest_service)],
) -> BaseResponse:
    """Logout guest by revoking refresh token and blocklisting access token."""
    guest: GuestModel = request.state.guest
    await service.logout_guest(
        refresh_token=body.refresh_token,
        access_token_jti=body.access_token_jti,
    )
    return BaseResponse(message="Logged out successfully")

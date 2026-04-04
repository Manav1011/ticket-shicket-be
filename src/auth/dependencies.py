from __future__ import annotations
from typing import Annotated, TYPE_CHECKING
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from auth.jwt import access
from db.session import db_session
from exceptions import UnauthorizedError, InvalidJWTTokenException

if TYPE_CHECKING:
    from apps.user.models import UserModel
    from apps.guest.models import GuestModel


security = HTTPBearer()


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(db_session),
) -> UserModel:
    """
    Dependency that validates Bearer token and returns the current user.
    Raises 401 if no valid token is provided. Also sets request.state.user.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        payload = access.decode(credentials.credentials)
        if payload.get("user_type") != "user":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type - expected user",
            )
        user_id = UUID(payload["sub"])
    except (UnauthorizedError, InvalidJWTTokenException, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    from apps.user.models import UserModel

    user = await session.scalar(
        select(UserModel).where(UserModel.id == user_id)
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    request.state.user = user
    return user


async def get_current_guest(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(db_session),
) -> GuestModel:
    """
    Dependency that validates Bearer token and returns the current guest.
    Validates token has type="guest".
    Raises 401 if no valid guest token is provided.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        payload = access.decode(credentials.credentials)
        if payload.get("user_type") != "guest":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type - expected guest",
            )
        guest_id = UUID(payload["sub"])
    except (UnauthorizedError, InvalidJWTTokenException, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    from apps.guest.models import GuestModel

    guest = await session.scalar(
        select(GuestModel).where(GuestModel.id == guest_id)
    )

    if not guest:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Guest not found",
        )

    if guest.is_converted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Guest has been converted",
        )

    request.state.guest = guest
    return guest

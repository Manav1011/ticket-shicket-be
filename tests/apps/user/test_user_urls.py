from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from apps.user.models import UserModel
from apps.user.request import DeleteUserByIdRequest, GetUserByIdRequest, SignUpRequest
from apps.user.urls import create_user, delete_user_by_id, get_user_by_id


@pytest.mark.asyncio
async def test_create_user_returns_only_public_fields():
    user = UserModel(
        id=uuid4(),
        first_name="Jane",
        last_name="Doe",
        email="jane@example.com",
        phone="1234567890",
        password="hashed-password",
    )
    service = AsyncMock()
    service.create_user.return_value = user
    body = SignUpRequest(
        first_name="Jane",
        last_name="Doe",
        email="jane@example.com",
        phone="1234567890",
        password="Secret123!",
    )

    response = await create_user(body=body, service=service)

    assert response.data.model_dump() == {
        "id": user.id,
        "first_name": "Jane",
        "last_name": "Doe",
    }


@pytest.mark.asyncio
async def test_get_user_by_id_rejects_other_user():
    current_user = SimpleNamespace(id=uuid4())
    request = SimpleNamespace(state=SimpleNamespace(user=current_user))
    query = GetUserByIdRequest(user_id=uuid4())
    service = AsyncMock()

    with pytest.raises(HTTPException) as excinfo:
        await get_user_by_id(query=query, request=request, service=service)

    assert excinfo.value.status_code == 403
    service.get_user_by_id.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_user_by_id_rejects_other_user():
    current_user = SimpleNamespace(id=uuid4())
    request = SimpleNamespace(state=SimpleNamespace(user=current_user))
    query = DeleteUserByIdRequest(user_id=uuid4())
    service = AsyncMock()

    with pytest.raises(HTTPException) as excinfo:
        await delete_user_by_id(query=query, request=request, service=service)

    assert excinfo.value.status_code == 403
    service.delete_user_by_id.assert_not_awaited()

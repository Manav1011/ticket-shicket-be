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
        phone="+919876543210",
        password="hashed-password",
    )
    service = AsyncMock()
    service.create_user.return_value = user
    body = SignUpRequest(
        first_name="Jane",
        last_name="Doe",
        email="jane@example.com",
        phone="+919876543210",
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


@pytest.mark.asyncio
async def test_find_user_by_email_returns_user():
    from apps.user.urls import find_user_endpoint
    from apps.user.response import UserLookupResponse

    user_id = uuid4()
    service = AsyncMock()
    service.find_user = AsyncMock(return_value=UserLookupResponse(
        user_id=user_id,
        email="alice@example.com",
        phone="9876543210",
        first_name="Alice",
        last_name="Smith",
    ))

    response = await find_user_endpoint(email="alice@example.com", phone=None, service=service)

    assert response.data.email == "alice@example.com"
    assert response.data.user_id == user_id
    service.find_user.assert_awaited_once_with(email="alice@example.com", phone=None)


@pytest.mark.asyncio
async def test_find_user_by_phone_returns_user():
    from apps.user.urls import find_user_endpoint
    from apps.user.response import UserLookupResponse

    user_id = uuid4()
    service = AsyncMock()
    service.find_user = AsyncMock(return_value=UserLookupResponse(
        user_id=user_id,
        email="bob@example.com",
        phone="9876543210",
        first_name="Bob",
        last_name="Jones",
    ))

    response = await find_user_endpoint(email=None, phone="9876543210", service=service)

    assert response.data.phone == "9876543210"
    service.find_user.assert_awaited_once_with(email=None, phone="9876543210")


@pytest.mark.asyncio
async def test_find_user_not_found_raises_error():
    from apps.user.urls import find_user_endpoint

    service = AsyncMock()
    service.find_user = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as excinfo:
        await find_user_endpoint(email="ghost@example.com", phone=None, service=service)

    assert excinfo.value.status_code == 404


@pytest.mark.asyncio
async def test_find_user_missing_params_raises_error():
    from apps.user.urls import find_user_endpoint

    service = AsyncMock()

    with pytest.raises(HTTPException) as excinfo:
        await find_user_endpoint(email=None, phone=None, service=service)

    assert excinfo.value.status_code == 400

from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest

from apps.ticketing.request import AllocateTicketTypeRequest, CreateTicketTypeRequest
from apps.ticketing.urls import create_ticket_allocation, create_ticket_type


@pytest.mark.asyncio
async def test_create_ticket_type_returns_ticket_type_dto():
    owner_id = uuid4()
    event_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=owner_id)))
    body = CreateTicketTypeRequest(name="General", category="PUBLIC", price=0, currency="INR")
    service = AsyncMock()
    service.create_ticket_type.return_value = SimpleNamespace(
        id=uuid4(),
        event_id=event_id,
        name="General",
        category="PUBLIC",
        price=0,
        currency="INR",
    )

    response = await create_ticket_type(
        event_id=event_id, request=request, body=body, service=service
    )

    assert response.data.name == "General"


@pytest.mark.asyncio
async def test_create_ticket_allocation_returns_allocation_dto():
    owner_id = uuid4()
    event_id = uuid4()
    event_day_id = uuid4()
    ticket_type_id = uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(id=owner_id)))
    body = AllocateTicketTypeRequest(
        event_day_id=event_day_id, ticket_type_id=ticket_type_id, quantity=25
    )
    service = AsyncMock()
    service.allocate_ticket_type_to_day.return_value = SimpleNamespace(
        id=uuid4(),
        event_day_id=event_day_id,
        ticket_type_id=ticket_type_id,
        quantity=25,
    )

    response = await create_ticket_allocation(
        event_id=event_id, request=request, body=body, service=service
    )

    assert response.data.event_day_id == event_day_id
    assert response.data.quantity == 25

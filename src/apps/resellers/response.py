from typing import Any
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime


class ResellerEventItem(BaseModel):
    event_id: UUID
    event_name: str
    organizer_name: str
    event_status: str
    my_role: str  # "reseller"
    accepted_at: datetime

    class Config:
        from_attributes = True


class ResellerEventsResponse(BaseModel):
    events: list[ResellerEventItem]
    total: int


class ResellerTicketItem(BaseModel):
    event_day_id: UUID
    count: int


class ResellerTicketsResponse(BaseModel):
    event_id: UUID
    holder_id: UUID | None
    tickets: list[ResellerTicketItem]
    total: int


class ResellerAllocationItem(BaseModel):
    allocation_id: UUID
    event_day_id: UUID
    direction: str  # "received" | "transferred"
    from_holder_id: UUID | None
    to_holder_id: UUID
    ticket_count: int
    status: str
    source: str
    created_at: datetime


class ResellerAllocationsResponse(BaseModel):
    event_id: UUID
    allocations: list[ResellerAllocationItem]
    total: int

from uuid import UUID

from utils.schema import BaseResponse, CamelCaseModel


class TicketTypeResponse(CamelCaseModel):
    id: UUID
    event_id: UUID
    name: str
    category: str
    price: float
    currency: str


class DayTicketAllocationResponse(CamelCaseModel):
    id: UUID
    event_day_id: UUID
    ticket_type_id: UUID
    quantity: int


class TicketTypeEnvelopeResponse(BaseResponse[TicketTypeResponse]):
    pass


class DayTicketAllocationEnvelopeResponse(BaseResponse[DayTicketAllocationResponse]):
    pass

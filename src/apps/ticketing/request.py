from uuid import UUID

from utils.schema import CamelCaseModel


class CreateTicketTypeRequest(CamelCaseModel):
    name: str
    category: str
    price: float
    currency: str = "INR"


class AllocateTicketTypeRequest(CamelCaseModel):
    event_day_id: UUID
    ticket_type_id: UUID
    quantity: int

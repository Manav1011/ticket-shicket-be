from uuid import UUID

from apps.ticketing.enums import TicketCategory
from utils.schema import CamelCaseModel


class CreateTicketTypeRequest(CamelCaseModel):
    name: str
    category: TicketCategory
    price: float
    currency: str = "INR"


class AllocateTicketTypeRequest(CamelCaseModel):
    event_day_id: UUID
    ticket_type_id: UUID
    quantity: int

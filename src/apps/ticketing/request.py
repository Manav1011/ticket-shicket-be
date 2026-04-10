from uuid import UUID

from pydantic import Field

from apps.ticketing.enums import TicketCategory
from utils.schema import CamelCaseModel


class CreateTicketTypeRequest(CamelCaseModel):
    name: str
    category: TicketCategory
    price: float = Field(gt=0)
    currency: str = "INR"


class AllocateTicketTypeRequest(CamelCaseModel):
    event_day_id: UUID
    ticket_type_id: UUID
    quantity: int = Field(gt=0)


class UpdateTicketAllocationQuantityRequest(CamelCaseModel):
    quantity: int = Field(gt=0)

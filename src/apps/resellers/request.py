from uuid import UUID
from pydantic import Field, model_validator
from utils.schema import CamelCaseModel
from apps.allocation.enums import TransferMode

class CreateResellerCustomerTransferRequest(CamelCaseModel):
    phone: str | None = None
    email: str | None = None
    quantity: int = Field(gt=0)
    event_day_id: UUID
    mode: TransferMode = TransferMode.FREE
    price: float | None = None  # Flat order price in rupees. Required when mode=PAID.

    @model_validator(mode='after')
    def must_have_phone_or_email(self):
        if not self.phone and not self.email:
            raise ValueError('Either phone or email must be provided')
        return self

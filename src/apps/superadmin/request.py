from pydantic import BaseModel, Field


class ApproveB2BRequestFreeBody(BaseModel):
    admin_notes: str | None = None


class ApproveB2BRequestPaidBody(BaseModel):
    amount: float = Field(gt=0)
    admin_notes: str | None = None


class RejectB2BRequestBody(BaseModel):
    reason: str | None = None

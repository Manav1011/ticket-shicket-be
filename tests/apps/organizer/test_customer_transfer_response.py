import pytest
from uuid import uuid4
from pydantic import ValidationError
from src.apps.organizer.response import CustomerTransferResponse


def test_valid_free_response():
    transfer_id = uuid4()
    resp = CustomerTransferResponse(
        transfer_id=transfer_id,
        status="completed",
        ticket_count=5,
        mode="free",
    )
    assert resp.transfer_id == transfer_id
    assert resp.status == "completed"
    assert "claim_link" not in resp.model_dump()


def test_valid_paid_not_implemented():
    transfer_id = uuid4()
    resp = CustomerTransferResponse(
        transfer_id=transfer_id,
        status="not_implemented",
        ticket_count=0,
        mode="paid",
        message="Paid transfer coming soon",
    )
    assert resp.status == "not_implemented"
    assert resp.message == "Paid transfer coming soon"


def test_rejects_invalid_mode():
    with pytest.raises(ValidationError):
        CustomerTransferResponse(
            transfer_id=uuid4(),
            status="completed",
            ticket_count=5,
            mode="invalid",
        )

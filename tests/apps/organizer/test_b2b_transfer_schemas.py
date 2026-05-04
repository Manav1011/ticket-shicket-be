import pytest
from uuid import uuid4
from apps.organizer.request import CreateB2BTransferRequest
from apps.organizer.response import B2BTransferResponse


def test_create_b2b_transfer_request_schema():
    req = CreateB2BTransferRequest(
        reseller_id=uuid4(),
        quantity=5,
        event_day_id=uuid4(),
        mode="free",
    )
    assert req.reseller_id is not None
    assert req.quantity == 5
    assert req.mode == "free"


def test_create_b2b_transfer_request_paid_mode():
    req = CreateB2BTransferRequest(
        reseller_id=uuid4(),
        quantity=3,
        event_day_id=None,
        mode="paid",
        price=100.0,
    )
    assert req.mode == "paid"
    assert req.price == 100.0


def test_b2b_transfer_response_schema():
    resp = B2BTransferResponse(
        transfer_id=uuid4(),
        status="completed",
        ticket_count=5,
        reseller_id=uuid4(),
        mode="free",
    )
    assert resp.status == "completed"
    assert resp.ticket_count == 5

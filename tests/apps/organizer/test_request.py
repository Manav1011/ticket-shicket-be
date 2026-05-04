# tests/apps/organizer/test_request.py
import pytest
from apps.organizer.request import CreateB2BTransferRequest, CreateCustomerTransferRequest
from apps.allocation.enums import TransferMode


def test_b2b_transfer_request_mode_accepts_transfer_mode_enum():
    req = CreateB2BTransferRequest(
        reseller_id="00000000-0000-0000-0000-000000000001",
        quantity=2,
        mode=TransferMode.FREE,
    )
    assert req.mode == TransferMode.FREE


def test_b2b_transfer_request_mode_accepts_paid_string():
    req = CreateB2BTransferRequest(
        reseller_id="00000000-0000-0000-0000-000000000001",
        quantity=2,
        mode="paid",
    )
    assert req.mode == TransferMode.PAID


def test_customer_transfer_request_mode_accepts_transfer_mode_enum():
    req = CreateCustomerTransferRequest(
        phone="+919999999999",
        quantity=1,
        event_day_id="00000000-0000-0000-0000-000000000001",
        mode=TransferMode.PAID,
    )
    assert req.mode == TransferMode.PAID

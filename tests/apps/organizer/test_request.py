# tests/apps/organizer/test_request.py
import pytest
from apps.organizer.request import CreateB2BTransferRequest, CreateCustomerTransferRequest
from apps.allocation.enums import TransferMode


def test_b2b_transfer_request_has_price_field():
    req = CreateB2BTransferRequest(
        reseller_id="00000000-0000-0000-0000-000000000001",
        quantity=5,
        mode=TransferMode.PAID,
        price=250.0,
    )
    assert req.price == 250.0


def test_customer_transfer_request_has_price_field():
    req = CreateCustomerTransferRequest(
        phone="+919999999999",
        quantity=3,
        event_day_id="00000000-0000-0000-0000-000000000001",
        mode=TransferMode.PAID,
        price=100.0,
    )
    assert req.price == 100.0


def test_b2b_transfer_request_price_defaults_to_none():
    req = CreateB2BTransferRequest(
        reseller_id="00000000-0000-0000-0000-000000000001",
        quantity=5,
    )
    assert req.price is None


def test_customer_transfer_request_price_defaults_to_none():
    req = CreateCustomerTransferRequest(
        phone="+919999999999",
        quantity=3,
        event_day_id="00000000-0000-0000-0000-000000000001",
    )
    assert req.price is None

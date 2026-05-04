# tests/apps/resellers/test_request.py
import pytest
from apps.resellers.request import CreateResellerCustomerTransferRequest
from apps.allocation.enums import TransferMode


def test_reseller_customer_transfer_request_has_price_field():
    req = CreateResellerCustomerTransferRequest(
        phone="+919999999999",
        quantity=2,
        event_day_id="00000000-0000-0000-0000-000000000001",
        mode=TransferMode.PAID,
        price=150.0,
    )
    assert req.price == 150.0


def test_reseller_customer_transfer_request_price_defaults_to_none():
    req = CreateResellerCustomerTransferRequest(
        phone="+919999999999",
        quantity=2,
        event_day_id="00000000-0000-0000-0000-000000000001",
    )
    assert req.price is None

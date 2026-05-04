# tests/apps/organizer/test_response.py
import pytest
from uuid import uuid4
from apps.organizer.response import B2BTransferResponse, CustomerTransferResponse
from apps.allocation.enums import TransferMode


def test_b2b_transfer_response_has_payment_url_field():
    resp = B2BTransferResponse(
        transfer_id=uuid4(),
        status="pending_payment",
        ticket_count=2,
        reseller_id=uuid4(),
        mode=TransferMode.PAID,
        message="Payment link sent",
    )
    assert hasattr(resp, "payment_url")
    assert resp.payment_url is None


def test_b2b_transfer_response_payment_url_set():
    resp = B2BTransferResponse(
        transfer_id=uuid4(),
        status="pending_payment",
        ticket_count=2,
        reseller_id=uuid4(),
        mode=TransferMode.PAID,
        payment_url="https://razorpay.in/abc",
    )
    assert resp.payment_url == "https://razorpay.in/abc"


def test_customer_transfer_response_has_payment_url_field():
    resp = CustomerTransferResponse(
        transfer_id=uuid4(),
        status="pending_payment",
        ticket_count=1,
        mode=TransferMode.PAID,
        payment_url="https://razorpay.in/xyz",
    )
    assert resp.payment_url == "https://razorpay.in/xyz"


def test_customer_transfer_response_mode_accepts_transfer_mode_enum():
    resp = CustomerTransferResponse(
        transfer_id=uuid4(),
        status="pending_payment",
        ticket_count=1,
        mode=TransferMode.FREE,
    )
    assert resp.mode == TransferMode.FREE

import pytest
from uuid import uuid4
from pydantic import ValidationError
from src.apps.organizer.request import CreateCustomerTransferRequest


def test_valid_with_phone():
    req = CreateCustomerTransferRequest(
        phone="+919999999999", quantity=5, event_day_id=uuid4()
    )
    assert req.phone == "+919999999999"
    assert req.quantity == 5


def test_valid_with_email():
    req = CreateCustomerTransferRequest(
        email="test@example.com", quantity=3, event_day_id=uuid4()
    )
    assert req.email == "test@example.com"


def test_valid_with_both():
    req = CreateCustomerTransferRequest(
        phone="+919999999999", email="test@example.com", quantity=2, event_day_id=uuid4()
    )
    assert req.phone and req.email


def test_rejects_empty():
    """Rejects when neither phone nor email provided."""
    with pytest.raises(ValidationError):
        CreateCustomerTransferRequest(quantity=5, event_day_id=uuid4())


def test_rejects_missing_event_day_id():
    """Rejects when event_day_id is not provided."""
    with pytest.raises(ValidationError):
        CreateCustomerTransferRequest(phone="+919999999999", quantity=5)


def test_validates_mode():
    req = CreateCustomerTransferRequest(
        phone="+919999999999", quantity=5, event_day_id=uuid4(), mode="free"
    )
    assert req.mode == "free"


def test_rejects_invalid_mode():
    with pytest.raises(ValidationError):
        CreateCustomerTransferRequest(
            phone="+919999999999", quantity=5, event_day_id=uuid4(), mode="invalid"
        )

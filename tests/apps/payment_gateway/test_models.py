"""Tests for Payment Gateway models."""
import pytest
from apps.payment_gateway.models import PaymentGatewayEventModel


def test_payment_gateway_event_model_has_expected_columns():
    """Verify all required columns exist on PaymentGatewayEventModel."""
    from sqlalchemy import inspect

    mapper = inspect(PaymentGatewayEventModel)
    columns = {c.name for c in mapper.columns}

    assert "id" in columns
    assert "order_id" in columns
    assert "event_type" in columns
    assert "gateway_event_id" in columns
    assert "payload" in columns
    assert "gateway_payment_id" in columns


def test_payment_gateway_event_model_has_dedup_constraint():
    """Verify unique constraint on (order_id, event_type, gateway_event_id) exists."""
    constraints = [c.name for c in PaymentGatewayEventModel.__table__.constraints if c.name]
    assert any("dedup" in c.lower() for c in constraints)


def test_payment_gateway_event_model_has_payment_id_constraint():
    """Verify unique constraint on gateway_payment_id exists."""
    constraints = [c.name for c in PaymentGatewayEventModel.__table__.constraints if c.name]
    assert any("payment_id" in c.lower() for c in constraints)

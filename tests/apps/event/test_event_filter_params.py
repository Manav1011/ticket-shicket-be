# tests/apps/event/test_event_filter_params.py
from datetime import date
import pytest
from apps.event.request import EventFilterParams


def test_default_values():
    params = EventFilterParams()
    assert params.sort_by == "created_at"
    assert params.order == "desc"
    assert params.limit == 20
    assert params.offset == 0


def test_status_validation_rejects_invalid():
    with pytest.raises(ValueError):
        EventFilterParams(status="invalid")


def test_access_type_validation_rejects_invalid():
    with pytest.raises(ValueError):
        EventFilterParams(event_access_type="invalid")


def test_order_validation_rejects_invalid():
    with pytest.raises(ValueError):
        EventFilterParams(order="invalid")


def test_valid_params_accepted():
    params = EventFilterParams(
        status="draft",
        event_access_type="open",
        date_from=date(2026, 1, 1),
        date_to=date(2026, 12, 31),
        search="meetup",
        sort_by="start_date",
        order="asc",
        limit=50,
        offset=10,
    )
    assert params.status == "draft"
    assert params.limit == 50

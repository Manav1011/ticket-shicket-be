import pytest
import uuid
from apps.event.models import EventResellerModel


def test_event_reseller_model_creation():
    reseller = EventResellerModel(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        event_id=uuid.uuid4(),
        invited_by_id=uuid.uuid4(),
        permissions={},
    )
    assert reseller.user_id is not None
    assert reseller.event_id is not None
    assert reseller.permissions == {}
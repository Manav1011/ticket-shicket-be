import pytest
from apps.user.invite.enums import InviteStatus


def test_invite_status_values():
    assert InviteStatus.pending == "pending"
    assert InviteStatus.accepted == "accepted"
    assert InviteStatus.declined == "declined"
    assert InviteStatus.cancelled == "cancelled"
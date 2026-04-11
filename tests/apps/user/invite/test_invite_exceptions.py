import pytest
from apps.user.invite.exceptions import InviteNotFound, InviteAlreadyProcessed, NotInviteRecipient


def test_invite_not_found():
    exc = InviteNotFound()
    assert exc.message == "Invite not found."


def test_invite_already_processed():
    exc = InviteAlreadyProcessed()
    assert exc.message == "Invite has already been processed."


def test_not_invite_recipient():
    exc = NotInviteRecipient()
    assert exc.message == "You are not the recipient of this invite."
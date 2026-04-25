import pytest
from src.utils.notifications.sms import mock_send_sms
from src.utils.notifications.whatsapp import mock_send_whatsapp
from src.utils.notifications.email import mock_send_email


def test_mock_send_sms_returns_true():
    result = mock_send_sms("+919999999999", "Your ticket code is ABC123")
    assert result is True


def test_mock_send_whatsapp_returns_true():
    result = mock_send_whatsapp("+919999999999", "Your ticket code is ABC123")
    assert result is True


def test_mock_send_email_returns_true():
    result = mock_send_email("test@example.com", "Your Tickets", "Here are your tickets")
    assert result is True

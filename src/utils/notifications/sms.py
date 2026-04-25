"""
Mock SMS notification utility.
No-op implementation — real SMS integration (e.g., Twilio) replaces this later.
"""
import logging

logger = logging.getLogger(__name__)


def mock_send_sms(to_phone: str, message: str, template: str | None = None) -> bool:
    """
    Send SMS to a phone number.

    Args:
        to_phone: Destination phone number (E.164 format)
        message: Message content
        template: Optional template name for logging

    Returns:
        True (always) — stub implementation
    """
    logger.info(
        f"[MOCK SMS] to={to_phone} template={template} message={message[:50]}..."
    )
    return True

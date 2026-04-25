"""
Mock Email notification utility.
No-op implementation — real email provider (e.g., AWS SES, SendGrid) replaces this later.
"""
import logging

logger = logging.getLogger(__name__)


def mock_send_email(to_email: str, subject: str, body: str) -> bool:
    """
    Send email.

    Args:
        to_email: Destination email address
        subject: Email subject
        body: Email body content

    Returns:
        True (always) — stub implementation
    """
    logger.info(
        f"[MOCK EMAIL] to={to_email} subject={subject} body={body[:50]}..."
    )
    return True

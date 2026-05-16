"""Razorpay client singleton."""
import logging
from typing import Optional

import razorpay

from config import settings

logger = logging.getLogger(__name__)


class RazorpayClient:
    """
    Singleton Razorpay client wrapping razorpay.Client.
    Initialized once with key_id + key_secret from settings.
    """
    _instance: Optional["RazorpayClient"] = None
    _client: Optional[razorpay.Client] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _get_client(self) -> razorpay.Client:
        if self._client is None:
            key_id = settings.RAZORPAY_KEY_ID
            key_secret = settings.RAZORPAY_KEY_SECRET
            if not key_id or not key_secret:
                raise RuntimeError("RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET must be set")
            self._client = razorpay.Client(
                auth=(key_id, key_secret),
            )
            logger.info("Razorpay client initialized")
        return self._client

    @property
    def order(self):
        return self._get_client().order

    @property
    def payment_link(self):
        return self._get_client().payment_link


def get_razorpay_client() -> RazorpayClient:
    """Return the singleton RazorpayClient instance."""
    return RazorpayClient()

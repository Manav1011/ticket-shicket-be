"""Webhook URL routes."""
import logging

from typing import Annotated

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import db_session
from apps.payment_gateway.handlers.razorpay import RazorpayWebhookHandler
from apps.payment_gateway.exceptions import WebhookVerificationError
from utils.schema import BaseResponse

logger = logging.getLogger(__name__)

# Create a separate router for webhooks
webhooks_router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


def get_webhook_handler(
    session: Annotated[AsyncSession, Depends(db_session)],
) -> RazorpayWebhookHandler:
    """Dependency to inject webhook handler with session."""
    return RazorpayWebhookHandler(session)


@webhooks_router.post("/razorpay")
async def razorpay_webhook(
    request: Request,
    handler: Annotated[RazorpayWebhookHandler, Depends(get_webhook_handler)],
) -> BaseResponse[dict]:
    """
    Receive Razorpay webhook at POST /webhooks/razorpay.
    X-Razorpay-Signature header is verified before processing.
    """
    try:
        body = await request.body()
        headers = dict(request.headers)
        print(f"\n{'='*60}")
        print(f"RAZORPAY WEBHOOK RECEIVED")
        print(f"{'='*60}")
        print(f"Headers: {headers}")
        print(f"Body (first 2000 chars): {body[:2000]}")
        print(f"{'='*60}\n")
        result = await handler.handle(body, headers)
        return BaseResponse(data=result)
    except WebhookVerificationError:
        logger.warning("Razorpay webhook signature verification failed")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    except Exception:
        logger.exception("Unexpected error processing Razorpay webhook")
        raise HTTPException(status_code=500, detail="Internal server error")

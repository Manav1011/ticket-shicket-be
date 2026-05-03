"""Webhook URL routes."""
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import db_session
from apps.payment_gateway.handlers.razorpay import RazorpayWebhookHandler
from utils.schema import BaseResponse

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
    body = await request.body()
    headers = dict(request.headers)
    result = await handler.handle(body, headers)
    return BaseResponse(data=result)

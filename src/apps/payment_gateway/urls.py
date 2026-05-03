from typing import Annotated
from fastapi import APIRouter, Body, Depends, status

from .request import CreateRequest, UpdateRequest
from .response import SampleResponse
from .service import Payment_GatewayService
from .repository import Payment_GatewayRepository
from db.session import db_session

router = APIRouter(prefix="/api/payment_gateway", tags=["Payment_Gateway"])


def get_payment_gateway_service(session: db_session) -> Payment_GatewayService:
    return Payment_GatewayService(Payment_GatewayRepository(session))


# Create your routes here
# Example:
# @router.post("")
# async def create_payment_gateway(
#     body: Annotated[CreateRequest, Body()],
#     service: Annotated[Payment_GatewayService, Depends(get_payment_gateway_service)],
# ):
#     pass

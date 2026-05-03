from typing import Annotated
from fastapi import APIRouter, Body, Depends, status

from .request import CreateRequest, UpdateRequest
from .response import SampleResponse
from .service import QueuesService
from .repository import QueuesRepository
from db.session import db_session

router = APIRouter(prefix="/api/queues", tags=["Queues"])


def get_queues_service(session: db_session) -> QueuesService:
    return QueuesService(QueuesRepository(session))


# Create your routes here
# Example:
# @router.post("")
# async def create_queues(
#     body: Annotated[CreateRequest, Body()],
#     service: Annotated[QueuesService, Depends(get_queues_service)],
# ):
#     pass

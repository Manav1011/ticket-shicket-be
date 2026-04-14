from typing import Annotated
from fastapi import APIRouter, Body, Depends, status

from .request import CreateRequest, UpdateRequest
from .response import SampleResponse
from .service import AllocationService
from .repository import AllocationRepository
from db.session import db_session

router = APIRouter(prefix="/api/allocation", tags=["Allocation"])


def get_allocation_service(session: db_session) -> AllocationService:
    return AllocationService(AllocationRepository(session))


# Create your routes here
# Example:
# @router.post("")
# async def create_allocation(
#     body: Annotated[CreateRequest, Body()],
#     service: Annotated[AllocationService, Depends(get_allocation_service)],
# ):
#     pass

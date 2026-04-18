from typing import Annotated

from fastapi import APIRouter, Depends

from auth.dependencies import get_current_user
from apps.core.response import EnumsResponse
from apps.core.service import EnumService
from utils.schema import BaseResponse

router = APIRouter(prefix="/api/enums", tags=["Enums"], dependencies=[Depends(get_current_user)])


def get_enum_service() -> EnumService:
    return EnumService()


@router.get("", operation_id="list_enums")
async def list_enums(
    service: Annotated[EnumService, Depends(get_enum_service)],
) -> BaseResponse[EnumsResponse]:
    data = service.list_enums()
    return BaseResponse(data=EnumsResponse.model_validate(data))

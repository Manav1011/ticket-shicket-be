from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependencies import get_current_super_admin
from apps.superadmin.models import SuperAdminModel
from apps.superadmin.request import (
    ApproveB2BRequestFreeBody,
    ApproveB2BRequestPaidBody,
    RejectB2BRequestBody,
)
from apps.superadmin.response import B2BRequestResponse
from apps.superadmin.service import SuperAdminService
from db.session import db_session
from utils.schema import BaseResponse

router = APIRouter(
    prefix="/api/superadmin",
    tags=["SuperAdmin"],
    dependencies=[Depends(get_current_super_admin)],
)


def get_super_admin_service(
    session: Annotated[AsyncSession, Depends(db_session)],
) -> SuperAdminService:
    return SuperAdminService(session)


@router.get("/b2b-requests")
async def list_b2b_requests(
    request: Request,
    service: Annotated[SuperAdminService, Depends(get_super_admin_service)],
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> BaseResponse[list[B2BRequestResponse]]:
    """
    [Super Admin] List all B2B requests, optionally filtered by status.
    """
    from apps.superadmin.enums import B2BRequestStatus

    admin = request.state.super_admin
    status_enum = B2BRequestStatus(status_filter) if status_filter else None
    requests = await service.list_all_b2b_requests(
        status=status_enum, limit=limit, offset=offset
    )
    return BaseResponse(data=[B2BRequestResponse.model_validate(r) for r in requests])


@router.get("/b2b-requests/pending")
async def list_pending_b2b_requests(
    request: Request,
    service: Annotated[SuperAdminService, Depends(get_super_admin_service)],
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> BaseResponse[list[B2BRequestResponse]]:
    """
    [Super Admin] List pending B2B requests awaiting review.
    """
    requests = await service.list_pending_b2b_requests(limit=limit, offset=offset)
    return BaseResponse(data=[B2BRequestResponse.model_validate(r) for r in requests])


@router.get("/b2b-requests/{request_id}")
async def get_b2b_request(
    request_id: UUID,
    request: Request,
    service: Annotated[SuperAdminService, Depends(get_super_admin_service)],
) -> BaseResponse[B2BRequestResponse]:
    """
    [Super Admin] Get a single B2B request by ID.
    """
    b2b_request = await service.get_b2b_request(request_id)
    return BaseResponse(data=B2BRequestResponse.model_validate(b2b_request))


@router.post("/b2b-requests/{request_id}/approve-free")
async def approve_b2b_request_free(
    request_id: UUID,
    request: Request,
    service: Annotated[SuperAdminService, Depends(get_super_admin_service)],
    body: Annotated[ApproveB2BRequestFreeBody, Body()],
) -> BaseResponse[B2BRequestResponse]:
    """
    [Super Admin] Approve B2B request as free transfer.
    Creates allocation immediately with $0 TRANSFER order.
    """
    admin = request.state.super_admin
    b2b_request = await service.approve_b2b_request_free(
        admin_id=admin.id,
        request_id=request_id,
        admin_notes=body.admin_notes,
    )
    return BaseResponse(data=B2BRequestResponse.model_validate(b2b_request))


@router.post("/b2b-requests/{request_id}/approve-paid")
async def approve_b2b_request_paid(
    request_id: UUID,
    request: Request,
    service: Annotated[SuperAdminService, Depends(get_super_admin_service)],
    body: Annotated[ApproveB2BRequestPaidBody, Body()],
) -> BaseResponse[B2BRequestResponse]:
    """
    [Super Admin] Approve B2B request as paid.
    Sets the amount and creates a pending PURCHASE order.
    Organizer then pays via the organizer app's confirm-payment endpoint.
    """
    admin = request.state.super_admin
    b2b_request = await service.approve_b2b_request_paid(
        admin_id=admin.id,
        request_id=request_id,
        amount=body.amount,
        admin_notes=body.admin_notes,
    )
    return BaseResponse(data=B2BRequestResponse.model_validate(b2b_request))


@router.post("/b2b-requests/{request_id}/reject")
async def reject_b2b_request(
    request_id: UUID,
    request: Request,
    service: Annotated[SuperAdminService, Depends(get_super_admin_service)],
    body: Annotated[RejectB2BRequestBody, Body()],
) -> BaseResponse[B2BRequestResponse]:
    """
    [Super Admin] Reject a B2B request.
    """
    admin = request.state.super_admin
    b2b_request = await service.reject_b2b_request(
        admin_id=admin.id,
        request_id=request_id,
        reason=body.reason,
    )
    return BaseResponse(data=B2BRequestResponse.model_validate(b2b_request))

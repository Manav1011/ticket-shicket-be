import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from apps.allocation.enums import AllocationStatus, AllocationType, ClaimLinkStatus
from src.apps.event.claim_service import ClaimService


@pytest.mark.asyncio
async def test_get_jwt_for_claim_token_success():
    """Valid active claim link returns JWT string."""
    session = AsyncMock()
    service = ClaimService(session)

    holder_id = uuid4()
    event_day_id = uuid4()
    claim_link = MagicMock()
    claim_link.id = uuid4()
    claim_link.status = ClaimLinkStatus.active
    claim_link.to_holder_id = holder_id
    claim_link.event_day_id = event_day_id
    claim_link.jwt_jti = "stored-jti"

    ticket_one = MagicMock()
    ticket_one.ticket_index = 2
    ticket_two = MagicMock()
    ticket_two.ticket_index = 1

    scalars_result = MagicMock()
    scalars_result.all.return_value = [ticket_one, ticket_two]
    session.scalars = AsyncMock(return_value=scalars_result)
    service._claim_link_repo.get_by_token_hash = AsyncMock(return_value=claim_link)

    with patch(
        "src.apps.event.claim_service.generate_scan_jwt",
        return_value="scan-jwt",
    ) as generate_scan_jwt:
        response = await service.get_claim_redemption("raw-token")

    assert response.jwt == "scan-jwt"
    assert response.ticket_count == 2
    assert "holder_id" not in response.model_dump()
    assert "event_day_id" not in response.model_dump()
    generate_scan_jwt.assert_called_once_with(
        jti="stored-jti",
        holder_id=holder_id,
        event_day_id=event_day_id,
        indexes=[1, 2],
    )
    stmt = session.scalars.await_args.args[0]
    assert "claim_link_id" in str(stmt)
    session.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_jwt_legacy_claim_link_no_claim_link_id():
    """Legacy claim links should still include untagged tickets owned by holder."""
    session = AsyncMock()
    service = ClaimService(session)

    holder_id = uuid4()
    event_day_id = uuid4()
    claim_link = MagicMock()
    claim_link.id = uuid4()
    claim_link.status = ClaimLinkStatus.active
    claim_link.to_holder_id = holder_id
    claim_link.event_day_id = event_day_id
    claim_link.jwt_jti = "stored-jti"

    ticket = MagicMock()
    ticket.ticket_index = 1

    scalars_result = MagicMock()
    scalars_result.all.return_value = [ticket]
    session.scalars = AsyncMock(return_value=scalars_result)
    service._claim_link_repo.get_by_token_hash = AsyncMock(return_value=claim_link)

    with patch(
        "src.apps.event.claim_service.generate_scan_jwt",
        return_value="scan-jwt",
    ):
        response = await service.get_claim_redemption("raw-token")

    assert response.ticket_count == 1
    stmt = session.scalars.await_args.args[0]
    stmt_text = str(stmt)
    assert "claim_link_id" in stmt_text
    assert "owner_holder_id" in stmt_text


@pytest.mark.asyncio
async def test_get_jwt_for_claim_token_not_found():
    """Invalid token raises NotFoundError."""
    pass


@pytest.mark.asyncio
async def test_get_jwt_for_claim_token_inactive():
    """Inactive claim link raises BadRequestError."""
    pass


@pytest.mark.asyncio
async def test_split_claim_transfers_tickets_and_reissues_jwt():
    session = AsyncMock()
    service = ClaimService(session)

    event_id = uuid4()
    event_day_id = uuid4()
    customer_a_id = uuid4()
    customer_b_id = uuid4()
    allocation_id = uuid4()
    source_order_id = uuid4()
    ticket_type_id = uuid4()
    locked_ticket_ids = [uuid4(), uuid4()]

    claim_link = MagicMock()
    claim_link.id = uuid4()
    claim_link.allocation_id = allocation_id
    claim_link.status = ClaimLinkStatus.active
    claim_link.to_holder_id = customer_a_id
    claim_link.event_id = event_id
    claim_link.event_day_id = event_day_id
    claim_link.jwt_jti = "old-jti"

    customer_b = MagicMock()
    customer_b.id = customer_b_id

    source_allocation = MagicMock()
    source_allocation.order_id = source_order_id

    ticket_type = MagicMock()
    ticket_type.id = ticket_type_id

    tickets = []
    for index in range(3):
        ticket = MagicMock()
        ticket.id = locked_ticket_ids[index] if index < 2 else uuid4()
        ticket.ticket_index = index
        tickets.append(ticket)

    scalars_result = MagicMock()
    scalars_result.all.return_value = tickets
    session.scalars = AsyncMock(return_value=scalars_result)

    service._claim_link_repo.get_by_token_hash = AsyncMock(return_value=claim_link)
    service._claim_link_repo.revoke_claim_link = AsyncMock()
    service._allocation_repo.resolve_holder = AsyncMock(return_value=customer_b)
    service._allocation_repo.get_allocation_by_id = AsyncMock(
        return_value=source_allocation
    )

    allocation = MagicMock()
    allocation.id = uuid4()
    customer_b_claim_link = MagicMock()
    customer_b_claim_link.id = uuid4()
    customer_b_claim_link.jwt_jti = None

    async def mock_create_allocation_with_claim_link(**kwargs):
        customer_b_claim_link.jwt_jti = kwargs.get("jwt_jti")
        return (allocation, customer_b_claim_link)

    mock_method = AsyncMock(side_effect=mock_create_allocation_with_claim_link)
    service._allocation_repo.create_allocation_with_claim_link = mock_method
    service._allocation_repo.add_tickets_to_allocation = AsyncMock()
    service._allocation_repo.upsert_edge = AsyncMock()
    service._allocation_repo.transition_allocation_status = AsyncMock(return_value=True)
    service._revoked_scan_token_repo.add_revoked_jti = AsyncMock()

    ticketing_repo = MagicMock()
    ticketing_repo.get_b2b_ticket_type_for_event = AsyncMock(return_value=ticket_type)
    ticketing_repo.lock_tickets_for_transfer = AsyncMock(return_value=locked_ticket_ids)
    ticketing_repo.update_ticket_ownership_batch = AsyncMock()

    with patch(
        "src.apps.event.claim_service.TicketingRepository",
        return_value=ticketing_repo,
    ), patch(
        "src.apps.event.claim_service.generate_claim_link_token",
        return_value="claimb123",
    ), patch(
        "src.apps.event.claim_service.secrets.token_hex",
        side_effect=["customer-b-jti", "customer-a-new-jti"],
    ):
        response = await service.split_claim(
            raw_token="raw-token",
            to_email="b@example.com",
            ticket_count=2,
        )

    assert response.status == "completed"
    assert response.tickets_transferred == 2
    assert response.remaining_ticket_count == 1
    assert response.new_jwt
    assert customer_b_claim_link.jwt_jti == "customer-b-jti"
    assert claim_link.jwt_jti == "customer-a-new-jti"

    ticketing_repo.lock_tickets_for_transfer.assert_awaited_once_with(
        owner_holder_id=customer_a_id,
        event_id=event_id,
        ticket_type_id=ticket_type_id,
        event_day_id=event_day_id,
        quantity=2,
        order_id=source_order_id,
    )
    service._allocation_repo.create_allocation_with_claim_link.assert_awaited_once()
    _, kwargs = service._allocation_repo.create_allocation_with_claim_link.await_args
    assert kwargs["allocation_type"] == AllocationType.transfer
    assert kwargs["ticket_count"] == 2
    assert kwargs["metadata_"] == {"source": "customer_split"}
    ticketing_repo.update_ticket_ownership_batch.assert_awaited_once_with(
        ticket_ids=locked_ticket_ids,
        new_owner_holder_id=customer_b_id,
        claim_link_id=customer_b_claim_link.id,
    )

    service._allocation_repo.transition_allocation_status.assert_awaited_once_with(
        allocation.id,
        AllocationStatus.pending,
        AllocationStatus.completed,
    )
    # Don't revoke claim link — Customer A's claim URL stays valid forever
    # Only jwt_jti is updated, old JTI is added to revoked list
    service._revoked_scan_token_repo.add_revoked_jti.assert_awaited_once_with(
        event_day_id=event_day_id,
        jti="old-jti",
        reason="split",
    )
    session.execute.assert_awaited_once()
    stmt = session.execute.await_args.args[0]
    assert "claim_link_id" in str(stmt)

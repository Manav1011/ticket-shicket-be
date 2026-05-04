"""Test that AllocationRepository prevents duplicate allocations per order."""
import pytest
from uuid import uuid4

from sqlalchemy import select
from apps.allocation.models import AllocationModel, OrderModel
from apps.allocation.repository import AllocationRepository
from apps.ticketing.enums import OrderType, OrderStatus


@pytest.mark.asyncio
async def test_create_allocation_with_duplicate_order_id_raises_integrity_error(db_session, test_user, test_event):
    """
    UNIQUE(order_id) constraint on AllocationModel prevents double-create.
    When a second allocation is created with the same order_id, IntegrityError is raised.
    """
    repo = AllocationRepository(db_session)

    # Need a real order in the DB because of ForeignKey constraint
    order = OrderModel(
        id=uuid4(),
        event_id=test_event.id,
        user_id=test_user.id,
        type=OrderType.transfer,
        subtotal_amount=0,
        final_amount=0,
        status=OrderStatus.paid
    )
    db_session.add(order)
    await db_session.flush()

    order_id = order.id

    # Create first allocation — should succeed
    allocation = await repo.create_allocation(
        event_id=test_event.id,
        from_holder_id=uuid4(),
        to_holder_id=uuid4(),
        order_id=order_id,
        allocation_type="transfer",
        ticket_count=2,
    )
    assert allocation.order_id == order_id

    # Create second allocation with same order_id — should raise
    from sqlalchemy.exc import IntegrityError
    with pytest.raises(IntegrityError):
        await repo.create_allocation(
            event_id=test_event.id,
            from_holder_id=uuid4(),
            to_holder_id=uuid4(),
            order_id=order_id,
            allocation_type="transfer",
            ticket_count=2,
        )
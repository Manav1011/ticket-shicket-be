import pytest
import hashlib
from uuid import uuid4
from datetime import datetime, timezone, date, timedelta
from sqlalchemy import select
from unittest.mock import AsyncMock, patch, MagicMock

from apps.payment_gateway.handlers.razorpay import RazorpayWebhookHandler
from apps.allocation.models import OrderModel, AllocationModel, TicketHolderModel, AllocationEdgeModel
from apps.ticketing.models import TicketModel, TicketTypeModel
from apps.event.models import EventModel, EventDayModel
from apps.organizer.models import OrganizerPageModel
from apps.allocation.enums import AllocationType, AllocationStatus
from apps.ticketing.enums import OrderStatus, TicketCategory, TicketStatus
from apps.payment_gateway.schemas.base import WebhookEvent

@pytest.mark.asyncio
async def test_paid_b2b_transfer_full_flow(db_session, test_user):
    # 1. Setup Organizer Page
    org_page = OrganizerPageModel(
        owner_user_id=test_user.id,
        name="Org Page",
        slug=f"org-page-{uuid4().hex[:8]}",
    )
    db_session.add(org_page)
    await db_session.flush()
    
    # 2. Setup Event
    event = EventModel(
        organizer_page_id=org_page.id,
        created_by_user_id=test_user.id,
        title="Paid Event",
        slug=f"paid-event-{uuid4().hex[:8]}",
    )
    db_session.add(event)
    await db_session.flush()

    # 3. Setup Event Day
    event_day = EventDayModel(
        event_id=event.id,
        day_index=0,
        date=date.today(),
    )
    db_session.add(event_day)
    
    # 4. Setup Ticket Type (B2B)
    ticket_type = TicketTypeModel(
        event_id=event.id,
        name="B2B Ticket",
        category=TicketCategory.b2b,
        price=1000.0,
    )
    db_session.add(ticket_type)
    await db_session.flush()

    # 5. Setup Holders
    org_holder = TicketHolderModel(user_id=test_user.id, phone="1111111111")
    reseller_user_id = uuid4()
    reseller_holder = TicketHolderModel(user_id=reseller_user_id, email=f"reseller-{uuid4().hex[:8]}@example.com")
    db_session.add_all([org_holder, reseller_holder])
    await db_session.flush()

    # 6. Setup Tickets owned by Organizer
    tickets = [
        TicketModel(
            event_id=event.id,
            event_day_id=event_day.id,
            ticket_type_id=ticket_type.id,
            ticket_index=i,
            owner_holder_id=org_holder.id,
            status=TicketStatus.active,
        )
        for i in range(2)
    ]
    db_session.add_all(tickets)
    await db_session.flush()

    # 7. Create Order (Simulate create_b2b_transfer mode=PAID)
    order = OrderModel(
        event_id=event.id,
        user_id=test_user.id,
        type="transfer",
        subtotal_amount=2000.0,
        discount_amount=0.0,
        final_amount=2000.0,
        status=OrderStatus.pending,
        sender_holder_id=org_holder.id,
        receiver_holder_id=reseller_holder.id,
        transfer_type="organizer_to_reseller",
        event_day_id=event_day.id,
        gateway_order_id="plink_test_123",
    )
    db_session.add(order)
    await db_session.flush()

    # 8. Lock tickets for the order
    for ticket in tickets:
        ticket.lock_reference_type = "transfer"
        ticket.lock_reference_id = order.id
        ticket.lock_expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
    await db_session.flush()

    # 9. Simulate Razorpay Webhook (order.paid)
    handler = RazorpayWebhookHandler(db_session)
    
    # Mock gateway
    handler._gateway = MagicMock()
    handler._gateway.verify_webhook_signature.return_value = True
    
    raw_payload = {
        "event": "order.paid",
        "payload": {
            "order": {
                "entity": {
                    "id": "plink_test_123",
                    "notes": {"internal_order_id": str(order.id)},
                }
            },
            "payment": {
                "entity": {
                    "id": "pay_test_123",
                    "order_id": "plink_test_123",
                    "amount": 200000,  # 2000.00 INR in paise
                    "status": "captured",
                }
            }
        }
    }
    event_schema = WebhookEvent(
        event="order.paid",
        gateway_order_id="plink_test_123",
        internal_order_id=str(order.id),
        receipt=None,
        raw_payload=raw_payload,
    )
    handler._gateway.parse_webhook_event.return_value = event_schema

    # Execute handler
    result = await handler.handle(b"{}", {})
    assert result["status"] == "ok"

    # 10. Verify results
    await db_session.refresh(order)
    assert order.status == OrderStatus.paid
    assert order.gateway_payment_id == "pay_test_123"

    # Verify allocation
    alloc_result = await db_session.execute(
        select(AllocationModel).where(AllocationModel.order_id == order.id)
    )
    allocation = alloc_result.scalar_one()
    assert allocation.status == AllocationStatus.completed
    assert allocation.to_holder_id == reseller_holder.id
    assert allocation.ticket_count == 2

    # Verify tickets transferred
    for ticket in tickets:
        await db_session.refresh(ticket)
        assert ticket.owner_holder_id == reseller_holder.id
        assert ticket.lock_reference_id is None
        assert ticket.lock_reference_type is None

    # Verify edge
    edge_result = await db_session.execute(
        select(AllocationEdgeModel).where(
            AllocationEdgeModel.from_holder_id == org_holder.id,
            AllocationEdgeModel.to_holder_id == reseller_holder.id,
        )
    )
    edge = edge_result.scalar_one()
    assert edge.ticket_count == 2

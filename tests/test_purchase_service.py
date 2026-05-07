import pytest
from uuid import uuid4, UUID
from unittest.mock import patch
from datetime import datetime, timezone
from apps.ticketing.models import TicketModel, TicketTypeModel, DayTicketAllocationModel
from apps.ticketing.enums import TicketCategory
from apps.allocation.models import CouponModel, OrderModel
from apps.ticketing.enums import TicketCategory
from apps.ticketing.enums import OrderType, OrderStatus
from apps.allocation.enums import GatewayType, CouponType, AllocationType, ClaimLinkStatus, AllocationStatus
from apps.allocation.repository import CouponRepository
from apps.event.service import PurchaseService


@pytest.fixture
async def purchase_service(db_session):
    from apps.event.repository import EventRepository
    return PurchaseService(
        coupon_repository=CouponRepository(db_session),
        repository=EventRepository(db_session),
    )


@pytest.fixture
async def published_event_setup(db_session, test_event):
    """Published event with ticket type, allocation, and 5 pool tickets."""
    # Set event to published state (required for purchase)
    test_event.is_published = True
    test_event.status = "published"
    await db_session.flush()

    from apps.event.models import EventDayModel
    day = EventDayModel(
        id=uuid4(),
        event_id=test_event.id,
        day_index=1,
        date=datetime(2026, 6, 15).date(),
    )
    db_session.add(day)

    ticket_type = TicketTypeModel(
        id=uuid4(),
        event_id=test_event.id,
        name="General Admission",
        category=TicketCategory.public,
        price=499.0,
        currency="INR",
    )
    db_session.add(ticket_type)

    allocation = DayTicketAllocationModel(
        id=uuid4(),
        event_day_id=day.id,
        ticket_type_id=ticket_type.id,
        quantity=5,
    )
    db_session.add(allocation)

    tickets = [
        TicketModel(
            id=uuid4(),
            event_id=test_event.id,
            event_day_id=day.id,
            ticket_type_id=ticket_type.id,
            ticket_index=i,
            owner_holder_id=None,
            status="active",
        )
        for i in range(5)
    ]
    db_session.add_all(tickets)
    await db_session.flush()
    return {
        "event": test_event,
        "day": day,
        "ticket_type": ticket_type,
        "tickets": tickets,
    }


@pytest.mark.asyncio
async def test_preview_order_returns_price_breakdown(published_event_setup, purchase_service):
    """Preview returns subtotal, discount, final without creating an order."""
    result = await purchase_service.preview_order(
        event_id=published_event_setup["event"].id,
        event_day_id=published_event_setup["day"].id,
        ticket_type_id=published_event_setup["ticket_type"].id,
        quantity=2,
        coupon_code=None,
    )
    assert result["subtotal_amount"] == "998.00"
    assert result["discount_amount"] == "0.00"
    assert result["final_amount"] == "998.00"
    assert result["coupon_applied"] is None


@pytest.mark.asyncio
async def test_preview_order_with_coupon(published_event_setup, purchase_service, db_session):
    """Preview applies a valid FLAT coupon."""
    coupon = CouponModel(
        id=uuid4(),
        code="FLAT100",
        type=CouponType.FLAT,
        value=100.0,
        max_discount=None,
        min_order_amount=0.0,
        usage_limit=100,
        per_user_limit=10,
        used_count=0,
        valid_from=datetime(2026, 1, 1),
        valid_until=datetime(2026, 12, 31),
        is_active=True,
    )
    db_session.add(coupon)
    await db_session.flush()

    result = await purchase_service.preview_order(
        event_id=published_event_setup["event"].id,
        event_day_id=published_event_setup["day"].id,
        ticket_type_id=published_event_setup["ticket_type"].id,
        quantity=2,
        coupon_code="FLAT100",
    )
    assert result["subtotal_amount"] == "998.00"
    assert result["discount_amount"] == "100.00"
    assert result["final_amount"] == "898.00"
    assert result["coupon_applied"]["code"] == "FLAT100"


@pytest.mark.asyncio
async def test_preview_order_quantity_exceeds_available(published_event_setup, purchase_service):
    """Preview raises BadRequestError when quantity > available pool."""
    from exceptions import BadRequestError
    with pytest.raises(BadRequestError) as exc_info:
        await purchase_service.preview_order(
            event_id=published_event_setup["event"].id,
            event_day_id=published_event_setup["day"].id,
            ticket_type_id=published_event_setup["ticket_type"].id,
            quantity=10,  # only 5 in pool
            coupon_code=None,
        )
    assert "Only 5 tickets available" in str(exc_info.value)


@pytest.fixture
async def buyer_holder(db_session, test_user):
    """TicketHolder for the buying user."""
    from apps.allocation.models import TicketHolderModel
    holder = TicketHolderModel(
        id=uuid4(),
        user_id=test_user.id,
        email="buyer@example.com",
        status="active",
    )
    db_session.add(holder)
    await db_session.flush()
    return holder


@pytest.mark.asyncio
async def test_create_order_happy_path(published_event_setup, buyer_holder, purchase_service, db_session, test_user):
    """create_order creates order and returns razorpay details."""
    from apps.ticketing.repository import TicketingRepository
    from apps.allocation.models import OrderModel
    from apps.ticketing.enums import OrderStatus
    from apps.payment_gateway.services.base import CheckoutOrderResult
    from unittest.mock import AsyncMock, patch

    order_id = uuid4()

    with patch.object(TicketingRepository, 'lock_tickets_for_purchase', new_callable=AsyncMock) as mock_lock:
        mock_lock.return_value = [t.id for t in published_event_setup["tickets"][:2]]

        with patch('apps.event.service.get_gateway', new_callable=AsyncMock) as mock_gateway:
            mock_gateway.return_value.create_checkout_order = AsyncMock(return_value=CheckoutOrderResult(
                gateway_order_id="razorpay_order_123",
                amount=99800,
                currency="INR",
                key_id="rzp_test_xxx",
                gateway_response={},
            ))

            result = await purchase_service.create_order(
                user_id=test_user.id,
                event_id=published_event_setup["event"].id,
                event_day_id=published_event_setup["day"].id,
                ticket_type_id=published_event_setup["ticket_type"].id,
                quantity=2,
                coupon_code=None,
                order_id=order_id,
            )

    assert result["order_id"] == order_id
    assert result["razorpay_order_id"] == "razorpay_order_123"
    assert result["status"] == "pending"

    # Verify order was created in DB
    db_session.expire_all()
    order = await db_session.get(OrderModel, order_id)
    assert order.status == OrderStatus.pending
    assert order.type == OrderType.purchase
    assert order.gateway_type.value == "razorpay_order"


@pytest.mark.asyncio
async def test_create_order_locks_are_cleared_on_failure(published_event_setup, buyer_holder, purchase_service, db_session, test_user):
    """If order creation fails after locking, locks are released."""
    from apps.ticketing.repository import TicketingRepository
    from unittest.mock import AsyncMock, patch

    order_id = uuid4()

    with patch.object(TicketingRepository, 'lock_tickets_for_purchase', new_callable=AsyncMock) as mock_lock:
        mock_lock.return_value = [t.id for t in published_event_setup["tickets"][:2]]

        # Simulate gateway failure
        with patch('apps.event.service.get_gateway', new_callable=AsyncMock) as mock_gateway:
            mock_gateway.return_value.create_checkout_order = AsyncMock(side_effect=Exception("Razorpay error"))

            with patch.object(TicketingRepository, 'clear_locks_for_order', new_callable=AsyncMock) as mock_clear:
                with pytest.raises(Exception):
                    await purchase_service.create_order(
                        user_id=test_user.id,
                        event_id=published_event_setup["event"].id,
                        event_day_id=published_event_setup["day"].id,
                        ticket_type_id=published_event_setup["ticket_type"].id,
                        quantity=2,
                        coupon_code=None,
                        order_id=order_id,
                    )

                # Verify locks were cleared after failure
                mock_clear.assert_called_once_with(order_id)


@pytest.mark.asyncio
async def test_poll_order_status_paid(purchase_service, db_session, test_user, published_event_setup):
    """poll_order_status returns paid status and claim link info."""
    from apps.allocation.models import OrderModel, ClaimLinkModel
    from apps.ticketing.enums import OrderStatus
    from apps.allocation.enums import ClaimLinkStatus

    order_id = uuid4()
    order = OrderModel(
        id=order_id,
        event_id=published_event_setup["event"].id,
        user_id=test_user.id,
        event_day_id=published_event_setup["day"].id,
        type=OrderType.purchase,
        subtotal_amount=499.0,
        discount_amount=0.0,
        final_amount=499.0,
        status=OrderStatus.paid,
        gateway_type=GatewayType.RAZORPAY_ORDER,
    )
    db_session.add(order)

    from apps.allocation.models import AllocationModel
    allocation = AllocationModel(
        id=uuid4(),
        order_id=order_id,
        event_id=published_event_setup["event"].id,
        from_holder_id=None,
        to_holder_id=uuid4(),
        allocation_type=AllocationType.purchase,
        status=AllocationStatus.completed,
        ticket_count=1,
    )
    db_session.add(allocation)

    claim_link = ClaimLinkModel(
        id=uuid4(),
        allocation_id=allocation.id,
        event_id=published_event_setup["event"].id,
        event_day_id=published_event_setup["day"].id,
        to_holder_id=allocation.to_holder_id,
        created_by_holder_id=allocation.to_holder_id,
        token_hash="hash_123",
        token="test_token_123",
        status=ClaimLinkStatus.active,
    )
    db_session.add(claim_link)
    await db_session.flush()

    with patch('apps.event.service.settings') as mock_settings:
        mock_settings.FRONTEND_URL = "https://example.com"
        
        result = await purchase_service.poll_order_status(order_id, test_user.id)
        
        assert result["status"] == "paid"
        assert result["ticket_count"] == 1
        assert "test_token_123" in result["claim_url"]
        assert result["jwt"] is not None


@pytest.mark.asyncio
async def test_poll_order_status_pending(purchase_service, db_session, test_user, published_event_setup):
    """poll_order_status returns pending when order is not paid yet."""
    from apps.allocation.models import OrderModel
    from apps.ticketing.enums import OrderStatus

    order_id = uuid4()
    order = OrderModel(
        id=order_id,
        event_id=published_event_setup["event"].id,
        user_id=test_user.id,
        event_day_id=published_event_setup["day"].id,
        type=OrderType.purchase,
        subtotal_amount=499.0,
        discount_amount=0.0,
        final_amount=499.0,
        status=OrderStatus.pending,
        gateway_type=GatewayType.RAZORPAY_ORDER,
    )
    db_session.add(order)
    await db_session.flush()

    result = await purchase_service.poll_order_status(order_id, test_user.id)
    assert result["status"] == "pending"
    assert result["claim_url"] is None

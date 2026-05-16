"""Tests for B2B Request Razorpay payment link flow."""
import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from apps.superadmin.service import SuperAdminService
from apps.superadmin.enums import B2BRequestStatus
from apps.superadmin.models import B2BRequestModel
from apps.allocation.enums import GatewayType
from apps.allocation.models import OrderModel
from apps.ticketing.enums import OrderType, OrderStatus
from sqlalchemy import select


class TestApproveB2bRequestPaidCreatesPaymentLink:
    """Test that approve_b2b_request_paid creates order + payment link."""

    async def test_approve_paid_creates_order_with_payment_link_fields(
        self, db_session, test_user, test_event
    ):
        """
        When Super Admin approves a B2B request as paid:
        - Order is created with gateway_type=RAZORPAY_PAYMENT_LINK
        - gateway_flow_type is set to 'b2b_request'
        - order_id is stored on the B2B request
        - B2B request status becomes approved_paid
        """
        from apps.ticketing.repository import TicketingRepository
        from apps.ticketing.models import TicketTypeModel
        from apps.event.models import EventDayModel

        # Create event day
        day = EventDayModel(
            event_id=test_event.id,
            day_index=0,
            date=date(2026, 12, 1),
            next_ticket_index=1,
        )
        db_session.add(day)
        await db_session.flush()

        # Create B2B ticket type
        ticketing_repo = TicketingRepository(db_session)
        b2b_type = await ticketing_repo.get_or_create_b2b_ticket_type(event_day_id=day.id)

        # Create B2B request
        b2b_request = B2BRequestModel(
            requesting_user_id=test_user.id,
            event_id=test_event.id,
            event_day_id=day.id,
            ticket_type_id=b2b_type.id,
            quantity=10,
            status=B2BRequestStatus.pending,
        )
        db_session.add(b2b_request)
        await db_session.flush()

        # Create super admin
        from apps.superadmin.models import SuperAdminModel
        super_admin = SuperAdminModel(user_id=uuid4(), name="Test Admin")
        db_session.add(super_admin)
        await db_session.flush()

        # Mock Razorpay payment link creation
        mock_payment_result = MagicMock()
        mock_payment_result.gateway_order_id = "plink_test_123"
        mock_payment_result.short_url = "https://razorpay.com/test"
        mock_payment_result.gateway_response = {"id": "plink_test_123"}

        with patch("apps.superadmin.service.get_gateway") as mock_get_gateway:
            mock_gateway = AsyncMock()
            mock_gateway.create_payment_link = AsyncMock(return_value=mock_payment_result)
            mock_get_gateway.return_value = mock_gateway

            svc = SuperAdminService(db_session)
            result = await svc.approve_b2b_request_paid(
                admin_id=super_admin.id,
                request_id=b2b_request.id,
                amount=5000.0,
                admin_notes="Approved at Rs. 50/ticket",
            )

        assert result.status == B2BRequestStatus.approved_paid
        assert result.order_id is not None

        # Verify order
        order = await db_session.scalar(
            select(OrderModel).where(OrderModel.id == result.order_id)
        )
        assert order is not None
        assert order.status.value == "pending"
        assert order.gateway_type == GatewayType.RAZORPAY_PAYMENT_LINK
        assert order.gateway_flow_type == "b2b_request"
        assert order.gateway_order_id == "plink_test_123"
        assert order.short_url == "https://razorpay.com/test"
        assert order.final_amount == 5000.0


class TestConfirmB2bPaymentNoOp:
    """Test that confirm_b2b_payment handles all cases correctly."""

    async def test_confirm_b2b_payment_already_paid_is_noop(
        self, db_session, test_user, test_event
    ):
        """
        When B2B request is already payment_done (paid via webhook),
        confirm_b2b_payment returns success without calling allocation.
        """
        from apps.ticketing.repository import TicketingRepository
        from apps.ticketing.models import TicketTypeModel
        from apps.event.models import EventDayModel
        from apps.organizer.service import OrganizerService
        from apps.organizer.repository import OrganizerRepository

        # Create event day
        day = EventDayModel(
            event_id=test_event.id,
            day_index=0,
            date=date(2026, 12, 1),
            next_ticket_index=1,
        )
        db_session.add(day)
        await db_session.flush()

        # Create B2B ticket type
        ticketing_repo = TicketingRepository(db_session)
        b2b_type = await ticketing_repo.get_or_create_b2b_ticket_type(event_day_id=day.id)

        # Create B2B request in payment_done status (paid via webhook)
        b2b_request = B2BRequestModel(
            requesting_user_id=test_user.id,
            event_id=test_event.id,
            event_day_id=day.id,
            ticket_type_id=b2b_type.id,
            quantity=10,
            status=B2BRequestStatus.payment_done,
        )
        db_session.add(b2b_request)
        await db_session.flush()

        repo = OrganizerRepository(db_session)
        svc = OrganizerService(repository=repo)
        result = await svc.confirm_b2b_payment(
            request_id=b2b_request.id,
            event_id=test_event.id,
            user_id=test_user.id,
        )

        assert result.status == B2BRequestStatus.payment_done

    async def test_confirm_b2b_payment_pending_payment_raises_error(
        self, db_session, test_user, test_event
    ):
        """
        When B2B request is still approved_paid (payment not made),
        confirm_b2b_payment raises SuperAdminError pointing to payment link.
        """
        from apps.ticketing.repository import TicketingRepository
        from apps.ticketing.models import TicketTypeModel
        from apps.event.models import EventDayModel
        from apps.organizer.service import OrganizerService
        from apps.organizer.repository import OrganizerRepository
        from apps.superadmin.exceptions import SuperAdminError

        # Create event day
        day = EventDayModel(
            event_id=test_event.id,
            day_index=0,
            date=date(2026, 12, 1),
            next_ticket_index=1,
        )
        db_session.add(day)
        await db_session.flush()

        # Create B2B ticket type
        ticketing_repo = TicketingRepository(db_session)
        b2b_type = await ticketing_repo.get_or_create_b2b_ticket_type(event_day_id=day.id)

        # Create B2B request in approved_paid status
        b2b_request = B2BRequestModel(
            requesting_user_id=test_user.id,
            event_id=test_event.id,
            event_day_id=day.id,
            ticket_type_id=b2b_type.id,
            quantity=10,
            status=B2BRequestStatus.approved_paid,
        )
        db_session.add(b2b_request)
        await db_session.flush()

        repo = OrganizerRepository(db_session)
        svc = OrganizerService(repository=repo)

        with pytest.raises(SuperAdminError, match="payment link"):
            await svc.confirm_b2b_payment(
                request_id=b2b_request.id,
                event_id=test_event.id,
                user_id=test_user.id,
            )

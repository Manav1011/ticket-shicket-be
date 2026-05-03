"""Razorpay webhook handler implementation."""
import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from apps.payment_gateway.exceptions import WebhookVerificationError
from apps.payment_gateway.repositories.event import PaymentGatewayEventRepository
from apps.payment_gateway.schemas.base import WebhookEvent
from apps.payment_gateway.services.factory import get_gateway
from apps.allocation.models import OrderModel
from apps.ticketing.enums import OrderStatus
from apps.ticketing.repository import TicketingRepository

logger = logging.getLogger(__name__)


class RazorpayWebhookHandler:
    """Handler for Razorpay webhooks."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self._gateway = get_gateway("razorpay")
        self._event_repo = PaymentGatewayEventRepository(session)
        self._ticketing_repo = TicketingRepository(session)

    async def handle(self, body: bytes, headers: dict) -> dict:
        """
        Verify signature, parse event, route to handler. Fully async.
        """
        if not self._gateway.verify_webhook_signature(body, headers):
            raise WebhookVerificationError("Webhook signature verification failed")

        event = self._gateway.parse_webhook_event(body, headers)

        if event.event == "order.paid":
            return await self.handle_order_paid(event)
        elif event.event == "payment.failed":
            return await self.handle_payment_failed(event)
        elif event.event == "payment_link.expired":
            return await self.handle_payment_link_expired(event)
        elif event.event == "payment_link.cancelled":
            return await self.handle_payment_link_cancelled(event)
        else:
            logger.info(f"Ignoring unhandled webhook event: {event.event}")
            return {"status": "ok"}

    async def handle_order_paid(self, event: WebhookEvent) -> dict:
        """Handle order.paid — 4-layer idempotent flow."""
        # Layer 1: Find order by internal_order_id or receipt
        internal_order_id = event.internal_order_id
        receipt = event.receipt

        if not internal_order_id and not receipt:
            logger.warning("Cannot find order: no internal_order_id or receipt in webhook")
            return {"status": "ok"}

        try:
            order_id = UUID(internal_order_id) if internal_order_id else UUID(receipt)
        except (ValueError, TypeError):
            logger.warning(f"Invalid order ID: internal_order_id={internal_order_id}, receipt={receipt}")
            return {"status": "ok"}

        result = await self.session.execute(
            select(OrderModel).where(OrderModel.id == order_id)
        )
        order = result.scalar_one_or_none()
        if not order:
            logger.warning(f"Order {order_id} not found")
            return {"status": "ok"}

        # Layer 1 (continued): skip if not pending
        if order.status != OrderStatus.pending:
            logger.info(f"Order {order_id} already {order.status} — ignoring late webhook")
            return {"status": "ok"}

        # Extract raw payload for validations
        raw = event.raw_payload
        razorpay_event_id = raw.get("id")

        # Layer 4: Event deduplication via DB constraint — attempt insert
        # IntegrityError on unique constraint violation = duplicate event
        try:
            payment_id = raw.get("payload", {}).get("payment", {}).get("entity", {}).get("id")
            if not payment_id:
                logger.error(f"No payment ID in webhook: {raw}")
                return {"status": "ok"}

            await self._event_repo.create(
                order_id=order.id,
                event_type="order.paid",
                gateway_event_id=razorpay_event_id,
                payload=raw,
                gateway_payment_id=payment_id,
            )
        except Exception as e:
            # Unique constraint violation — duplicate event, ignore
            logger.info(f"Duplicate order.paid event {razorpay_event_id} for order {order_id}: {str(e)}")
            return {"status": "ok"}

        # Validate gateway_order_id match
        webhook_order_id = raw.get("payload", {}).get("order", {}).get("entity", {}).get("id")
        if not webhook_order_id or order.gateway_order_id != webhook_order_id:
            logger.error(f"gateway_order_id mismatch: {order.gateway_order_id} vs {webhook_order_id}")
            return {"status": "ok"}

        # Validate payment.order_id matches webhook order id
        payment_order_id = raw.get("payload", {}).get("payment", {}).get("entity", {}).get("order_id")
        if payment_order_id != webhook_order_id:
            logger.error(f"payment.order_id ({payment_order_id}) != order.id ({webhook_order_id})")
            return {"status": "ok"}

        # Validate amount
        payment_amount = raw.get("payload", {}).get("payment", {}).get("entity", {}).get("amount")
        expected_amount = int(float(order.final_amount) * 100) if order.final_amount else 0
        if payment_amount != expected_amount:
            await self.session.execute(
                update(OrderModel)
                .where(OrderModel.id == order.id, OrderModel.status == OrderStatus.pending)
                .values(
                    status=OrderStatus.failed,
                    failure_reason=f"amount_mismatch: expected {expected_amount}, got {payment_amount}",
                )
            )
            await self._ticketing_repo.clear_locks_for_order(order.id)
            await self._gateway.cancel_payment_link(order.gateway_order_id)
            logger.warning(f"Order {order_id} amount mismatch, marked failed")
            return {"status": "ok"}

        # Validate payment status — only captured
        payment_status = raw.get("payload", {}).get("payment", {}).get("entity", {}).get("status")
        if payment_status != "captured":
            logger.info(f"Payment not yet captured: {payment_status}")
            return {"status": "ok"}

        # Layer 3: Atomic UPDATE — only succeeds if still pending
        updated = await self.session.execute(
            update(OrderModel)
            .where(OrderModel.id == order.id, OrderModel.status == OrderStatus.pending)
            .values(
                status=OrderStatus.paid,
                captured_at=datetime.now(timezone.utc),
                gateway_payment_id=payment_id,
                gateway_response=raw,
            )
        )
        if updated.rowcount == 0:
            logger.info(f"Order {order_id} already processed by another thread")
            return {"status": "ok"}

        # Layer 2: Create allocation (idempotent via UNIQUE constraint on order_id)
        # Phase 4: Allocation creation will be filled in next phase
        # For Phase 3, just clear locks and return success
        # TODO (Phase 4): Create allocation, transfer ticket ownership, upsert edge
        # Allocation creation will be idempotent via UNIQUE constraint on order_id
        # await self._allocation_repo.create_allocation(...)
        await self._ticketing_repo.clear_locks_for_order(order.id)

        logger.info(f"Order {order_id} marked paid, payment {payment_id}")
        return {"status": "ok"}

    async def handle_payment_failed(self, event: WebhookEvent) -> dict:
        """Handle payment.failed — atomic update + clear locks."""
        raw = event.raw_payload
        gateway_order_id = raw.get("payload", {}).get("payment", {}).get("entity", {}).get("order_id")
        
        if not gateway_order_id:
            gateway_order_id = event.gateway_order_id

        if not gateway_order_id:
            logger.warning("Cannot find gateway_order_id in payment.failed event")
            return {"status": "ok"}

        result = await self.session.execute(
            select(OrderModel).where(OrderModel.gateway_order_id == gateway_order_id)
        )
        order = result.scalar_one_or_none()
        if not order or order.status != OrderStatus.pending:
            return {"status": "ok"}

        error_description = raw.get("payload", {}).get("payment", {}).get("entity", {}).get(
            "error_description", "payment_failed"
        )

        updated = await self.session.execute(
            update(OrderModel)
            .where(OrderModel.id == order.id, OrderModel.status == OrderStatus.pending)
            .values(
                status=OrderStatus.failed,
                failure_reason=error_description,
            )
        )
        if updated.rowcount == 0:
            return {"status": "ok"}

        await self._ticketing_repo.clear_locks_for_order(order.id)
        logger.info(f"Order {order.id} marked failed: {error_description}")
        return {"status": "ok"}

    async def handle_payment_link_expired(self, event: WebhookEvent) -> dict:
        """Handle payment_link.expired — atomic update + clear locks + cancel link."""
        gateway_order_id = event.gateway_order_id

        if not gateway_order_id:
            logger.warning("Cannot find gateway_order_id in payment_link.expired event")
            return {"status": "ok"}

        result = await self.session.execute(
            select(OrderModel).where(OrderModel.gateway_order_id == gateway_order_id)
        )
        order = result.scalar_one_or_none()
        if not order or order.status != OrderStatus.pending:
            return {"status": "ok"}

        updated = await self.session.execute(
            update(OrderModel)
            .where(OrderModel.id == order.id, OrderModel.status == OrderStatus.pending)
            .values(
                status=OrderStatus.expired,
                expired_at=datetime.now(timezone.utc),
            )
        )
        if updated.rowcount == 0:
            return {"status": "ok"}

        await self._ticketing_repo.clear_locks_for_order(order.id)
        await self._gateway.cancel_payment_link(gateway_order_id)
        logger.info(f"Order {order.id} expired — payment link cancelled")
        return {"status": "ok"}

    async def handle_payment_link_cancelled(self, event: WebhookEvent) -> dict:
        """Handle payment_link.cancelled — same as expired with reason."""
        gateway_order_id = event.gateway_order_id

        if not gateway_order_id:
            logger.warning("Cannot find gateway_order_id in payment_link.cancelled event")
            return {"status": "ok"}

        result = await self.session.execute(
            select(OrderModel).where(OrderModel.gateway_order_id == gateway_order_id)
        )
        order = result.scalar_one_or_none()
        if not order or order.status != OrderStatus.pending:
            return {"status": "ok"}

        updated = await self.session.execute(
            update(OrderModel)
            .where(OrderModel.id == order.id, OrderModel.status == OrderStatus.pending)
            .values(
                status=OrderStatus.expired,
                expired_at=datetime.now(timezone.utc),
                failure_reason="payment_link_cancelled",
            )
        )
        if updated.rowcount == 0:
            return {"status": "ok"}

        await self._ticketing_repo.clear_locks_for_order(order.id)
        logger.info(f"Order {order.id} expired — payment link cancelled by organizer")
        return {"status": "ok"}

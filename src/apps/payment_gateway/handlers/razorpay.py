"""Razorpay webhook handler implementation."""
import hashlib
import logging
import secrets
from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.payment_gateway.exceptions import WebhookVerificationError
from apps.payment_gateway.models import PaymentGatewayEventModel
from apps.payment_gateway.repositories.event import PaymentGatewayEventRepository
from apps.payment_gateway.schemas.base import WebhookEvent
from apps.payment_gateway.services.factory import get_gateway
from apps.allocation.models import OrderModel, TicketHolderModel
from apps.allocation.enums import AllocationStatus, AllocationType, GatewayType
from apps.allocation.repository import AllocationRepository
from apps.ticketing.enums import OrderStatus
from apps.ticketing.models import TicketModel
from apps.ticketing.repository import TicketingRepository
from apps.superadmin.models import B2BRequestModel
from apps.superadmin.enums import B2BRequestStatus
from utils.claim_link_utils import generate_claim_link_token

logger = logging.getLogger(__name__)


class RazorpayWebhookHandler:
    """Handler for Razorpay webhooks."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self._gateway = get_gateway("razorpay")
        self._event_repo = PaymentGatewayEventRepository(session)
        self._ticketing_repo = TicketingRepository(session)
        self._allocation_repo = AllocationRepository(session)

    async def handle(self, body: bytes, headers: dict) -> dict:
        """
        Verify signature, parse event, route to handler. Fully async.
        Routings based on gateway_type:
        - RAZORPAY_ORDER: only process order.paid
        - RAZORPAY_PAYMENT_LINK: only process payment_link.paid
        """
        if not self._gateway.verify_webhook_signature(body, headers):
            raise WebhookVerificationError("Webhook signature verification failed")

        event = self._gateway.parse_webhook_event(body, headers)
        order = await self._find_order_for_event(event)
        gateway_type = order.gateway_type if order else None

        if event.event == "order.paid":
            if gateway_type == GatewayType.RAZORPAY_PAYMENT_LINK:
                logger.info("Ignoring order.paid for RAZORPAY_PAYMENT_LINK order")
                return {"status": "ok"}
            return await self.handle_order_paid(event)

        elif event.event == "payment.authorized":
            logger.info("Ignoring payment.authorized (handled by order.paid or payment_link.paid)")
            return {"status": "ok"}

        elif event.event == "payment.captured":
            logger.info("Ignoring payment.captured (handled by order.paid or payment_link.paid)")
            return {"status": "ok"}

        elif event.event == "payment_link.paid":
            if gateway_type == GatewayType.RAZORPAY_ORDER:
                logger.info("Ignoring payment_link.paid for RAZORPAY_ORDER order")
                return {"status": "ok"}
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

    async def _find_order_for_event(self, event: WebhookEvent) -> OrderModel | None:
        """
        Find order from webhook event for routing decision.
        Tries internal_order_id/receipt first, then gateway_order_id.
        """
        order_id = None
        if event.internal_order_id or event.receipt:
            try:
                order_id = UUID(event.internal_order_id) if event.internal_order_id else UUID(event.receipt)
            except (ValueError, TypeError):
                pass

        if order_id:
            result = await self.session.execute(select(OrderModel).where(OrderModel.id == order_id))
            return result.scalar_one_or_none()

        if event.gateway_order_id:
            result = await self.session.execute(
                select(OrderModel).where(OrderModel.gateway_order_id == event.gateway_order_id)
            )
            return result.scalar_one_or_none()

        return None

    async def handle_order_paid(self, event: WebhookEvent) -> dict:
        """Handle order.paid — 4-layer idempotent flow."""
        internal_order_id = event.internal_order_id
        receipt = event.receipt
        gateway_order_id = event.gateway_order_id

        # Find order — try internal_order_id/receipt first, fall back to gateway_order_id
        order_id = None
        if internal_order_id or receipt:
            try:
                order_id = UUID(internal_order_id) if internal_order_id else UUID(receipt)
            except (ValueError, TypeError):
                logger.warning(f"Invalid order ID: internal_order_id={internal_order_id}, receipt={receipt}")
                return {"status": "ok"}

        if not order_id and gateway_order_id:
            # Fall back to gateway_order_id lookup for payment_link.paid
            result = await self.session.execute(
                select(OrderModel).where(OrderModel.gateway_order_id == gateway_order_id)
            )
            order = result.scalar_one_or_none()
            if order:
                order_id = order.id

        if not order_id:
            logger.warning("Cannot find order: no internal_order_id, receipt, or gateway_order_id")
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

            # Pre-check: has this payment_id already been recorded?
            existing = await self.session.execute(
                select(PaymentGatewayEventModel).where(
                    PaymentGatewayEventModel.gateway_payment_id == payment_id
                )
            )
            if existing.scalar_one_or_none():
                logger.info(f"Duplicate payment {payment_id} — ignoring")
                return {"status": "ok"}

            await self._event_repo.create(
                order_id=order.id,
                event_type="order.paid",
                gateway_event_id=razorpay_event_id,
                payload=raw,
                gateway_payment_id=payment_id,
            )
        except IntegrityError:
            # Race condition: another thread inserted between pre-check and create
            # Rollback to reset poisoned session state
            await self.session.rollback()
            logger.info(f"Duplicate payment {payment_id} (race)")
            return {"status": "ok"}

        # Validate gateway_order_id match — gateway-type-specific
        if order.gateway_type == GatewayType.RAZORPAY_PAYMENT_LINK:
            # For payment links: order.gateway_order_id is plink_xxx, validate against event.gateway_order_id
            if event.gateway_order_id and order.gateway_order_id != event.gateway_order_id:
                logger.error(f"gateway_order_id mismatch for payment_link: {order.gateway_order_id} vs {event.gateway_order_id}")
                return {"status": "ok"}
        elif order.gateway_type == GatewayType.RAZORPAY_ORDER:
            # For checkout orders: order.gateway_order_id == payload.order.entity.id (same Razorpay order ID)
            webhook_order_id = raw.get("payload", {}).get("order", {}).get("entity", {}).get("id")
            if webhook_order_id and order.gateway_order_id != webhook_order_id:
                logger.error(f"gateway_order_id mismatch for order: {order.gateway_order_id} vs {webhook_order_id}")
                return {"status": "ok"}
        # gateway_type is NULL → skip validation, proceed (legacy orders)

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
                captured_at=datetime.utcnow(),
                gateway_payment_id=payment_id,
                gateway_response=raw,
            )
        )
        if updated.rowcount == 0:
            logger.info(f"Order {order_id} already processed by another thread")
            return {"status": "ok"}

        # Retrieve locked tickets and branch based on gateway type
        if order.gateway_type == GatewayType.RAZORPAY_ORDER:
            # Online purchase: tickets locked with lock_reference_type='order'
            locked_tickets_result = await self.session.execute(
                select(TicketModel).where(
                    TicketModel.lock_reference_type == 'order',
                    TicketModel.lock_reference_id == order.id,
                )
            )
            locked_ticket_ids = [t.id for t in locked_tickets_result.scalars().all()]

            if not locked_ticket_ids:
                logger.warning(f"No locked tickets found for order {order.id} after payment")
                await self._ticketing_repo.clear_locks_for_order(order.id)
                logger.info(f"Order {order_id} marked paid, payment {payment_id}")
                return {"status": "ok"}

            # Create allocation + claim link for buyer
            raw_token = generate_claim_link_token(length=8)
            token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

            allocation, claim_link = await self._allocation_repo.create_allocation_with_claim_link(
                event_id=order.event_id,
                event_day_id=order.event_day_id,
                from_holder_id=None,  # From pool (no previous owner)
                to_holder_id=order.receiver_holder_id,  # Buyer
                order_id=order.id,
                allocation_type=AllocationType.purchase,
                ticket_count=len(locked_ticket_ids),
                token_hash=token_hash,
                created_by_holder_id=order.receiver_holder_id,
                jwt_jti=secrets.token_hex(8),
                token=raw_token,
                metadata_={"source": "online_purchase"},
            )

            # Transfer ownership to buyer
            await self._ticketing_repo.update_ticket_ownership_batch(
                ticket_ids=locked_ticket_ids,
                new_owner_holder_id=order.receiver_holder_id,
                claim_link_id=claim_link.id,
            )

            # Add tickets to allocation
            await self._allocation_repo.add_tickets_to_allocation(allocation.id, locked_ticket_ids)

            # Upsert edge (pool → buyer)
            await self._allocation_repo.upsert_edge(
                event_id=order.event_id,
                from_holder_id=None,  # pool
                to_holder_id=order.receiver_holder_id,
                ticket_count=len(locked_ticket_ids),
            )

            # Mark allocation completed
            await self._allocation_repo.transition_allocation_status(
                allocation.id,
                AllocationStatus.pending,
                AllocationStatus.completed,
            )

            # Send claim link notifications to buyer
            from utils.notifications.sms import mock_send_sms
            from utils.notifications.whatsapp import mock_send_whatsapp
            from utils.notifications.email import mock_send_email

            holder_result = await self.session.execute(
                select(TicketHolderModel).where(TicketHolderModel.id == order.receiver_holder_id)
            )
            receiver_holder = holder_result.scalar_one_or_none()

            claim_url = f"/claim/{raw_token}"
            message = f"You purchased {len(locked_ticket_ids)} ticket(s). Claim at: {claim_url}"

            print(f"\n[PAID ONLINE PURCHASE WEBHOOK] Claim URL: http://0.0.0.0:8080/api/open{claim_url}\n")

            if receiver_holder and receiver_holder.phone:
                mock_send_sms(receiver_holder.phone, message, template="online_purchase")
                mock_send_whatsapp(receiver_holder.phone, message, template="online_purchase")
            if receiver_holder and receiver_holder.email:
                mock_send_email(receiver_holder.email, "Your ticket purchase is complete!", message)

            logger.info(f"Sent claim link to buyer for online purchase order {order.id}")

            await self._ticketing_repo.clear_locks_for_order(order.id)
            logger.info(f"Order {order_id} marked paid, payment {payment_id}")
            return {"status": "ok"}

        # Phase 3b: B2B Request paid — look up B2B request, then process allocation
        if order.gateway_flow_type == "b2b_request":
            logger.info(f"Routing B2B request payment for order {order.id}")

            # Look up the B2B request that references this order
            b2b_req_result = await self.session.execute(
                select(B2BRequestModel).where(B2BRequestModel.order_id == order.id)
            )
            b2b_request = b2b_req_result.scalar_one_or_none()
            if not b2b_request:
                logger.error(f"No B2B request found for order {order.id}")
                return {"status": "ok"}

            from apps.superadmin.service import SuperAdminService
            svc = SuperAdminService(self.session)
            await svc.process_paid_b2b_allocation(request_id=b2b_request.id)
            logger.info(f"B2B request {b2b_request.id} allocation complete for order {order.id}")
            return {"status": "ok", "b2b_request_id": str(b2b_request.id)}

        # Phase 4: Create B2B allocation + transfer tickets to buyer
        # Retrieve the locked tickets (locked during paid transfer creation in organizer service)
        # Tickets have lock_reference_type='transfer' and lock_reference_id=order.id
        locked_tickets_result = await self.session.execute(
            select(TicketModel).where(
                TicketModel.lock_reference_type == 'transfer',
                TicketModel.lock_reference_id == order.id,
            )
        )
        locked_ticket_ids = [t.id for t in locked_tickets_result.scalars().all()]

        if locked_ticket_ids:
            transfer_type = order.transfer_type
            is_reseller = transfer_type == "organizer_to_reseller"

            if is_reseller:
                # Reseller already has an account; no claim link needed
                allocation = await self._allocation_repo.create_allocation(
                    event_id=order.event_id,
                    from_holder_id=order.sender_holder_id,
                    to_holder_id=order.receiver_holder_id,
                    order_id=order.id,
                    allocation_type=AllocationType.b2b,
                    ticket_count=len(locked_ticket_ids),
                    metadata_={
                        "source": "razorpay_webhook_paid_transfer",
                        "transfer_type": transfer_type,
                    },
                )
            else:
                # Customer: create allocation with claim link
                raw_token = generate_claim_link_token(length=8)
                token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

                allocation, claim_link = await self._allocation_repo.create_allocation_with_claim_link(
                    event_id=order.event_id,
                    event_day_id=order.event_day_id,
                    from_holder_id=order.sender_holder_id,
                    to_holder_id=order.receiver_holder_id,
                    order_id=order.id,
                    allocation_type=AllocationType.b2b,
                    ticket_count=len(locked_ticket_ids),
                    token_hash=token_hash,
                    created_by_holder_id=order.sender_holder_id,
                    jwt_jti=secrets.token_hex(8),
                    token=raw_token,
                    metadata_={
                        "source": "razorpay_webhook_paid_transfer",
                        "transfer_type": transfer_type,
                    },
                )
                # Send claim link to customer via notification
                from utils.notifications.sms import mock_send_sms
                from utils.notifications.whatsapp import mock_send_whatsapp
                from utils.notifications.email import mock_send_email

                # Get receiver holder for contact info
                holder_result = await self.session.execute(
                    select(TicketHolderModel).where(TicketHolderModel.id == order.receiver_holder_id)
                )
                receiver_holder = holder_result.scalar_one()

                claim_url = f"/claim/{raw_token}"
                message = f"You received {len(locked_ticket_ids)} ticket(s). Claim at: {claim_url}"

                print(f"\n[PAID CUSTOMER TRANSFER WEBHOOK] Claim URL: http://0.0.0.0:8080/api/open{claim_url}\n")

                if receiver_holder.phone:
                    mock_send_sms(receiver_holder.phone, message, template="customer_transfer")
                    mock_send_whatsapp(receiver_holder.phone, message, template="customer_transfer")
                if receiver_holder.email:
                    mock_send_email(receiver_holder.email, "You received tickets!", message)

                logger.info(f"Sent claim link to customer for order {order.id}")

            # Add tickets to allocation
            await self._allocation_repo.add_tickets_to_allocation(allocation.id, locked_ticket_ids)

            # Upsert edge
            await self._allocation_repo.upsert_edge(
                event_id=order.event_id,
                from_holder_id=order.sender_holder_id,
                to_holder_id=order.receiver_holder_id,
                ticket_count=len(locked_ticket_ids),
            )

            # Transfer ownership
            await self._ticketing_repo.update_ticket_ownership_batch(
                ticket_ids=locked_ticket_ids,
                new_owner_holder_id=order.receiver_holder_id,
                claim_link_id=claim_link.id,
            )

            # Mark completed
            await self._allocation_repo.transition_allocation_status(
                allocation.id,
                AllocationStatus.pending,
                AllocationStatus.completed,
            )
        else:
            logger.warning(f"No locked tickets found for order {order.id} after payment")

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
        await self._gateway.cancel_payment_link(order.gateway_order_id)
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
                expired_at=datetime.utcnow(),
            )
        )
        if updated.rowcount == 0:
            return {"status": "ok"}

        await self._ticketing_repo.clear_locks_for_order(order.id)
        await self._gateway.cancel_payment_link(gateway_order_id)

        # B2B Request — also update the B2B request to expired
        if order.gateway_flow_type == "b2b_request":
            b2b_req_result = await self.session.execute(
                select(B2BRequestModel).where(B2BRequestModel.order_id == order.id)
            )
            b2b_req = b2b_req_result.scalar_one_or_none()
            if b2b_req and b2b_req.status == B2BRequestStatus.approved_paid:
                await self.session.execute(
                    update(B2BRequestModel)
                    .where(B2BRequestModel.id == b2b_req.id)
                    .values(status=B2BRequestStatus.expired.value)
                )
                await self.session.flush()

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
                expired_at=datetime.utcnow(),
                failure_reason="payment_link_cancelled",
            )
        )
        if updated.rowcount == 0:
            return {"status": "ok"}

        await self._ticketing_repo.clear_locks_for_order(order.id)

        # B2B Request — also update the B2B request to expired
        if order.gateway_flow_type == "b2b_request":
            b2b_req_result = await self.session.execute(
                select(B2BRequestModel).where(B2BRequestModel.order_id == order.id)
            )
            b2b_req = b2b_req_result.scalar_one_or_none()
            if b2b_req and b2b_req.status == B2BRequestStatus.approved_paid:
                await self.session.execute(
                    update(B2BRequestModel)
                    .where(B2BRequestModel.id == b2b_req.id)
                    .values(status=B2BRequestStatus.expired.value)
                )
                await self.session.flush()

        logger.info(f"Order {order.id} expired — payment link cancelled by organizer")
        return {"status": "ok"}

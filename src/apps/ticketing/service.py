from sqlalchemy.exc import IntegrityError

from apps.event.enums import EventAccessType
from apps.ticketing.enums import TicketCategory, TicketCategoryPublic
from src.exceptions import BadRequestError

from .exceptions import (
    CannotDecreaseQuantity,
    DuplicateAllocation,
    InvalidAllocation,
    InvalidPrice,
    InvalidQuantity,
    OpenEventDoesNotSupportTickets,
    TicketTypeNotFound,
)
from .models import TicketTypeModel


class TicketingService:
    def __init__(self, repository, event_repository, event_day_repository) -> None:
        self.repository = repository
        self.event_repository = event_repository
        self.event_day_repository = event_day_repository

    async def create_ticket_type(
        self, owner_user_id, event_id, name, category, price, currency
    ):
        event = await self.event_repository.get_by_id_for_owner(event_id, owner_user_id)
        if event.event_access_type != EventAccessType.ticketed:
            raise OpenEventDoesNotSupportTickets

        # Reject B2B category - B2B ticket types are auto-created internally
        if category == TicketCategory.b2b:
            raise BadRequestError("B2B ticket types are auto-created and cannot be created manually.")

        # C2: Validate price >= 0
        if price < 0:
            raise InvalidPrice

        ticket_type = TicketTypeModel(
            event_id=event_id,
            name=name,
            category=category,
            price=price,
            currency=currency,
        )
        self.repository.add(ticket_type)
        await self.repository.session.flush()
        await self.repository.session.refresh(ticket_type)
        return ticket_type

    async def list_ticket_types(self, owner_user_id, event_id):
        event = await self.event_repository.get_by_id_for_owner(event_id, owner_user_id)
        if event is None:
            return []
        return await self.repository.list_ticket_types_for_event(event_id)

    async def list_allocations(self, owner_user_id, event_id):
        event = await self.event_repository.get_by_id_for_owner(event_id, owner_user_id)
        if event is None:
            return []
        return await self.repository.list_allocations_for_event(event_id)

    async def allocate_ticket_type_to_day(
        self, owner_user_id, event_id, event_day_id, ticket_type_id, quantity
    ):
        event = await self.event_repository.get_by_id_for_owner(event_id, owner_user_id)
        if event.event_access_type != EventAccessType.ticketed:
            raise OpenEventDoesNotSupportTickets

        # C1: Verify ticket type belongs to this event
        ticket_type = await self.repository.get_ticket_type_for_event(ticket_type_id, event_id)
        if not ticket_type:
            raise TicketTypeNotFound

        # B2B ticket types cannot be allocated via this endpoint — use organizer B2B transfer instead
        if ticket_type.category == TicketCategory.b2b:
            raise InvalidAllocation("B2B ticket types cannot be allocated via this endpoint. Use B2B transfer.")

        # C1: Verify day belongs to this event
        day = await self.event_day_repository.get_event_day_for_owner(
            event_day_id, owner_user_id
        )
        if not day or day.event_id != event_id:
            raise InvalidAllocation("Event day does not belong to this event")

        # I1: Validate quantity > 0
        if quantity <= 0:
            raise InvalidQuantity

        # C3: Handle duplicate allocation gracefully
        try:
            allocation = await self.repository.create_day_allocation(
                event_day_id, ticket_type_id, quantity
            )
        except IntegrityError as e:
            if "uq_day_ticket_allocations" in str(e):
                raise DuplicateAllocation
            raise

        await self.repository.bulk_create_tickets(
            event_id,
            event_day_id,
            ticket_type_id,
            start_index=day.next_ticket_index,
            quantity=quantity,
        )
        day.next_ticket_index += quantity
        await self.repository.session.flush()
        return allocation

    async def update_allocation_quantity(
        self, owner_user_id, event_id, allocation_id, new_quantity
    ):
        # C1: Verify event ownership
        event = await self.event_repository.get_by_id_for_owner(event_id, owner_user_id)
        if event is None:
            raise InvalidAllocation("Event not found or access denied")

        # C1: Verify allocation exists
        allocation = await self.repository.get_allocation_by_id(allocation_id)
        if allocation is None:
            raise InvalidAllocation("Allocation not found")

        # C1: Verify allocation belongs to this event
        day = await self.event_day_repository.get_event_day_for_owner(
            allocation.event_day_id, owner_user_id
        )
        if day is None or day.event_id != event_id:
            raise InvalidAllocation("Allocation does not belong to this event")

        # I1: Validate new quantity > 0
        if new_quantity <= 0:
            raise InvalidQuantity

        # I1: Prevent quantity decrease
        if new_quantity < allocation.quantity:
            raise CannotDecreaseQuantity

        # C4: If no change, return allocation as-is (idempotent)
        if new_quantity == allocation.quantity:
            return allocation

        # C4: Calculate quantity increase and bulk-create new tickets
        quantity_increase = new_quantity - allocation.quantity
        await self.repository.bulk_create_tickets(
            event_id,
            allocation.event_day_id,
            allocation.ticket_type_id,
            start_index=day.next_ticket_index,
            quantity=quantity_increase,
        )

        # C4: Update allocation and day state
        allocation.quantity = new_quantity
        day.next_ticket_index += quantity_increase
        await self.repository.session.flush()
        await self.repository.session.refresh(allocation)
        return allocation

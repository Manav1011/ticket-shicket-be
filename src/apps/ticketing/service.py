from sqlalchemy.exc import IntegrityError

from apps.event.enums import EventAccessType

from .exceptions import (
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

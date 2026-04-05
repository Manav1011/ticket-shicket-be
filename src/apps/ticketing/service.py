from .exceptions import OpenEventDoesNotSupportTickets, TicketTypeNotFound
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
        if event.event_access_type != "ticketed":
            raise OpenEventDoesNotSupportTickets

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
        if event.event_access_type != "ticketed":
            raise OpenEventDoesNotSupportTickets

        ticket_type = await self.repository.get_ticket_type_for_event(ticket_type_id, event_id)
        if not ticket_type:
            raise TicketTypeNotFound

        day = await self.event_day_repository.get_event_day_for_owner(
            event_day_id, owner_user_id
        )
        allocation = await self.repository.create_day_allocation(
            event_day_id, ticket_type_id, quantity
        )
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

from uuid import UUID

from exceptions import NotFoundError


class PublicEventService:
    def __init__(self, event_repository, ticketing_repository) -> None:
        self.event_repo = event_repository
        self.ticketing_repo = ticketing_repository

    async def list_public_events(self) -> list:
        return await self.event_repo.list_published_events()

    async def get_public_event(self, event_id: UUID) -> dict:
        event = await self.event_repo.get_by_id(event_id)
        if not event:
            raise NotFoundError("Event not found")

        if not getattr(event, "is_published", False):
            raise NotFoundError("Event not found")

        days = await self.event_repo.list_event_days(event_id)
        assets = await self.event_repo.list_media_assets(event_id)
        ticket_types = await self.ticketing_repo.list_ticket_types_for_event(event_id)
        allocations = await self.ticketing_repo.list_allocations_for_event(event_id)

        return {
            "id": event.id,
            "title": event.title,
            "slug": getattr(event, "slug", None),
            "description": getattr(event, "description", None),
            "event_type": getattr(event, "event_type", None),
            "status": event.status,
            "event_access_type": getattr(event, "event_access_type", None),
            "location_mode": getattr(event, "location_mode", None),
            "timezone": getattr(event, "timezone", None),
            "start_date": getattr(event, "start_date", None),
            "end_date": getattr(event, "end_date", None),
            "venue_name": getattr(event, "venue_name", None),
            "venue_address": getattr(event, "venue_address", None),
            "venue_city": getattr(event, "venue_city", None),
            "venue_state": getattr(event, "venue_state", None),
            "venue_country": getattr(event, "venue_country", None),
            "venue_latitude": getattr(event, "venue_latitude", None),
            "venue_longitude": getattr(event, "venue_longitude", None),
            "online_event_url": getattr(event, "online_event_url", None),
            "recorded_event_url": getattr(event, "recorded_event_url", None),
            "published_at": getattr(event, "published_at", None),
            "is_published": getattr(event, "is_published", False),
            "interested_counter": getattr(event, "interested_counter", 0),
            "days": [
                {
                    "id": str(d.id),
                    "day_index": d.day_index,
                    "date": str(d.date),
                    "start_time": str(d.start_time) if d.start_time else None,
                    "end_time": str(d.end_time) if d.end_time else None,
                    "scan_status": d.scan_status,
                }
                for d in days
            ],
            "media_assets": [
                {
                    "id": str(a.id),
                    "asset_type": a.asset_type,
                    "public_url": a.public_url,
                    "title": getattr(a, "title", None),
                    "caption": getattr(a, "caption", None),
                    "alt_text": getattr(a, "alt_text", None),
                    "sort_order": a.sort_order,
                    "is_primary": a.is_primary,
                }
                for a in assets
            ],
            "ticket_types": [
                {
                    "id": str(t.id),
                    "name": getattr(t, "name", None),
                    "description": getattr(t, "description", None),
                    "price": str(getattr(t, "price", "0.00")),
                    "currency": getattr(t, "currency", "USD"),
                }
                for t in ticket_types
            ],
            "ticket_allocations": [
                {
                    "id": str(a.id),
                    "ticket_type_id": str(a.ticket_type_id),
                    "event_day_id": str(a.event_day_id),
                    "quantity": a.quantity,
                    "price": str(getattr(a, "price", "0.00")),
                }
                for a in allocations
            ],
        }

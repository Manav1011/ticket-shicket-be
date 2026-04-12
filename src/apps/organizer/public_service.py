from uuid import UUID

from exceptions import NotFoundError

from .models import OrganizerPageModel


class PublicOrganizerService:
    def __init__(self, repository) -> None:
        self.repository = repository

    async def list_organizers(self) -> list[OrganizerPageModel]:
        return await self.repository.list_public_organizers()

    async def get_organizer(self, organizer_id: UUID) -> OrganizerPageModel:
        organizer = await self.repository.get_by_id(organizer_id)
        if not organizer:
            raise NotFoundError("Organizer not found")
        return organizer

    async def list_events_by_organizer(self, organizer_id: UUID) -> list:
        return await self.repository.list_events_by_organizer_public(organizer_id)

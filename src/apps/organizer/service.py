import re

from .exceptions import OrganizerSlugAlreadyExists
from .models import OrganizerPageModel


class OrganizerService:
    def __init__(self, repository) -> None:
        self.repository = repository

    async def list_organizers(self, owner_user_id):
        return await self.repository.list_by_owner(owner_user_id)

    async def create_organizer(self, owner_user_id, name, slug, bio, visibility):
        normalized_slug = re.sub(r"[^a-z0-9]+", "-", slug.strip().lower()).strip("-")
        if await self.repository.get_by_slug(normalized_slug):
            raise OrganizerSlugAlreadyExists

        organizer = OrganizerPageModel(
            owner_user_id=owner_user_id,
            name=name.strip(),
            slug=normalized_slug,
            bio=bio,
            visibility=visibility,
            status="active",
        )
        self.repository.add(organizer)
        await self.repository.session.flush()
        await self.repository.session.refresh(organizer)
        return organizer

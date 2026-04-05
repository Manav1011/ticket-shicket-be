import re

from .exceptions import OrganizerNotFound, OrganizerSlugAlreadyExists
from .models import OrganizerPageModel


class OrganizerService:
    def __init__(self, repository) -> None:
        self.repository = repository

    async def list_organizers(self, owner_user_id):
        return await self.repository.list_by_owner(owner_user_id)

    async def list_organizer_events(self, owner_user_id, organizer_id, status=None):
        return await self.repository.list_events_for_owner(owner_user_id, organizer_id, status)

    async def create_organizer(
        self,
        owner_user_id,
        name,
        slug,
        bio,
        logo_url,
        cover_image_url,
        website_url,
        instagram_url,
        facebook_url,
        youtube_url,
        visibility,
    ):
        normalized_slug = re.sub(r"[^a-z0-9]+", "-", slug.strip().lower()).strip("-")
        if await self.repository.get_by_slug(normalized_slug):
            raise OrganizerSlugAlreadyExists

        organizer = OrganizerPageModel(
            owner_user_id=owner_user_id,
            name=name.strip(),
            slug=normalized_slug,
            bio=bio,
            logo_url=logo_url,
            cover_image_url=cover_image_url,
            website_url=website_url,
            instagram_url=instagram_url,
            facebook_url=facebook_url,
            youtube_url=youtube_url,
            visibility=visibility,
            status="active",
        )
        self.repository.add(organizer)
        await self.repository.session.flush()
        await self.repository.session.refresh(organizer)
        return organizer

    async def update_organizer(self, owner_user_id, organizer_id, **payload):
        organizer = await self.repository.get_by_id_for_owner(organizer_id, owner_user_id)
        if not organizer:
            raise OrganizerNotFound

        if "slug" in payload and payload["slug"] is not None:
            normalized_slug = re.sub(r"[^a-z0-9]+", "-", payload["slug"].strip().lower()).strip("-")
            existing = await self.repository.get_by_slug(normalized_slug)
            if existing and existing.id != organizer_id:
                raise OrganizerSlugAlreadyExists
            payload["slug"] = normalized_slug

        for field, value in payload.items():
            setattr(organizer, field, value)

        await self.repository.session.flush()
        await self.repository.session.refresh(organizer)
        return organizer

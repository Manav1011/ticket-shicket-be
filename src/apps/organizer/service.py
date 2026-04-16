import re
import uuid
from uuid import UUID

from .exceptions import OrganizerNotFound, OrganizerSlugAlreadyExists
from .models import OrganizerPageModel
from src.utils.s3_client import get_s3_client
from src.utils.file_validation import FileValidator, FileValidationError
from apps.superadmin.service import SuperAdminService
from apps.superadmin.enums import B2BRequestStatus


from apps.ticketing.repository import TicketingRepository


class OrganizerService:
    def __init__(self, repository) -> None:
        self.repository = repository
        self._super_admin_service = SuperAdminService(repository.session)
        self._ticketing_repo = TicketingRepository(repository.session)

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

    async def upload_logo(
        self,
        owner_user_id: UUID,
        organizer_page_id: UUID,
        file_name: str,
        file_content: bytes,
    ) -> OrganizerPageModel:
        """
        Upload logo image for organizer page.

        Args:
            owner_user_id: Page owner
            organizer_page_id: Organizer page UUID
            file_name: Original filename
            file_content: File bytes

        Returns:
            Updated OrganizerPageModel with logo_url

        Raises:
            OrganizerNotFound: If organizer page doesn't exist or user doesn't own it
            FileValidationError: If file validation fails
        """
        # Verify ownership
        organizer = await self.repository.get_by_id_for_owner(
            organizer_page_id, owner_user_id
        )
        if not organizer:
            raise OrganizerNotFound

        # Validate logo image (required: max 5MB, jpg/png/webp, min 200x200)
        FileValidator.validate_banner_image(file_name, file_content)

        # Upload to S3: organizers/{organizer_id}/logo_{uuid}_{filename}
        s3_client = get_s3_client()
        storage_key = s3_client.upload_file(
            resource_id=organizer_page_id,
            asset_type="logo",
            file_name=file_name,
            file_content=file_content,
            path_prefix="organizers",
        )
        public_url = s3_client.generate_public_url(storage_key)

        # Update organizer page
        organizer.logo_url = public_url
        await self.repository.session.flush()
        await self.repository.session.refresh(organizer)
        return organizer

    async def upload_cover_image(
        self,
        owner_user_id: UUID,
        organizer_page_id: UUID,
        file_name: str,
        file_content: bytes,
    ) -> OrganizerPageModel:
        """
        Upload cover image for organizer page.

        Args:
            owner_user_id: Page owner
            organizer_page_id: Organizer page UUID
            file_name: Original filename
            file_content: File bytes

        Returns:
            Updated OrganizerPageModel with cover_image_url

        Raises:
            OrganizerNotFound: If organizer page doesn't exist or user doesn't own it
            FileValidationError: If file validation fails
        """
        # Verify ownership
        organizer = await self.repository.get_by_id_for_owner(
            organizer_page_id, owner_user_id
        )
        if not organizer:
            raise OrganizerNotFound

        # Validate cover image (reuse banner validation: max 5MB, jpg/png/webp, min 200x200)
        FileValidator.validate_banner_image(file_name, file_content)

        # Upload to S3: organizers/{organizer_id}/cover_{uuid}_{filename}
        s3_client = get_s3_client()
        storage_key = s3_client.upload_file(
            resource_id=organizer_page_id,
            asset_type="cover",
            file_name=file_name,
            file_content=file_content,
            path_prefix="organizers",
        )
        public_url = s3_client.generate_public_url(storage_key)

        # Update organizer page
        organizer.cover_image_url = public_url
        await self.repository.session.flush()
        await self.repository.session.refresh(organizer)
        return organizer

    # --- B2B Request Methods ---

    async def create_b2b_request(
        self,
        user_id: uuid.UUID,
        event_id: uuid.UUID,
        event_day_id: uuid.UUID,
        quantity: int,
    ):
        """[Organizer] Submit a B2B ticket request. System auto-derives B2B ticket type."""
        # Auto-derive B2B ticket type for this event day
        b2b_ticket_type = await self._ticketing_repo.get_or_create_b2b_ticket_type(
            event_day_id=event_day_id,
        )
        return await self.repository.create_b2b_request(
            requesting_user_id=user_id,
            event_id=event_id,
            event_day_id=event_day_id,
            ticket_type_id=b2b_ticket_type.id,
            quantity=quantity,
        )

    async def get_b2b_requests_for_event(
        self,
        event_id: uuid.UUID,
    ) -> list:
        """[Organizer] List B2B requests for a specific event."""
        return await self.repository.list_b2b_requests_by_event(event_id)

    async def confirm_b2b_payment(
        self,
        request_id: uuid.UUID,
        event_id: uuid.UUID,
        user_id: uuid.UUID,
    ):
        """
        [Organizer] Confirm payment for an approved paid B2B request.
        Verifies user owns the organizer page that owns this event, then triggers allocation.
        """
        from exceptions import ForbiddenError

        # Verify the B2B request belongs to this event
        b2b_req = await self.repository.get_b2b_request_by_id(request_id)
        if not b2b_req or b2b_req.event_id != event_id:
            raise ForbiddenError("B2B request does not belong to this event")

        return await self._super_admin_service.process_paid_b2b_allocation(
            request_id=request_id,
        )

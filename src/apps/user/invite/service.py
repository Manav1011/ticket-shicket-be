from uuid import UUID

from .exceptions import InviteNotFound, InviteAlreadyProcessed, NotInviteRecipient
from .models import InviteModel
from .enums import InviteStatus, InviteType


class InviteService:
    def __init__(self, repository, user_repository) -> None:
        self.repository = repository
        self.user_repository = user_repository

    async def create_invite(
        self,
        target_user_id: UUID,
        created_by_id: UUID,
        metadata: dict,
        invite_type: str = InviteType.reseller.value,
    ) -> InviteModel:
        event_id = metadata.get("event_id")
        if event_id:
            existing = await self.repository.get_pending_invite_for_user_event(
                target_user_id, event_id
            )
            if existing:
                raise InviteAlreadyProcessed(
                    "A pending invite already exists for this user and event"
                )
        invite = InviteModel(
            target_user_id=target_user_id,
            created_by_id=created_by_id,
            status=InviteStatus.pending.value,
            invite_type=invite_type,
            meta=metadata,
        )
        self.repository.add(invite)
        await self.repository.session.flush()
        await self.repository.session.refresh(invite)
        return invite

    async def list_pending_invites_for_user(self, user_id: UUID) -> list[InviteModel]:
        return await self.repository.list_pending_invites_for_user(user_id)

    async def get_invite_by_id(self, invite_id: UUID) -> InviteModel:
        invite = await self.repository.get_invite_by_id(invite_id)
        if not invite:
            raise InviteNotFound
        return invite

    async def accept_invite(self, user_id: UUID, invite_id: UUID) -> dict:
        invite = await self.get_invite_by_id(invite_id)

        if invite.target_user_id != user_id:
            raise NotInviteRecipient

        if invite.status != InviteStatus.pending.value:
            raise InviteAlreadyProcessed

        await self.repository.update_invite_status(invite, InviteStatus.accepted.value)

        meta = invite.meta or {}
        return {
            "invite": invite,
            "event_id": meta.get("event_id"),
            "permissions": meta.get("permissions", {}),
        }

    async def decline_invite(self, user_id: UUID, invite_id: UUID) -> None:
        invite = await self.get_invite_by_id(invite_id)

        if invite.target_user_id != user_id:
            raise NotInviteRecipient

        if invite.status != InviteStatus.pending.value:
            raise InviteAlreadyProcessed

        await self.repository.update_invite_status(invite, InviteStatus.declined.value)

    async def cancel_invite(self, creator_id: UUID, invite_id: UUID) -> None:
        invite = await self.get_invite_by_id(invite_id)

        if invite.created_by_id != creator_id:
            from exceptions import ForbiddenError
            raise ForbiddenError("Only the invite creator can cancel it")

        if invite.status != InviteStatus.pending.value:
            raise InviteAlreadyProcessed

        await self.repository.update_invite_status(invite, InviteStatus.cancelled.value)
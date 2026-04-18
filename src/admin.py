"""
Admin integration helper for Starlette-Admin.

This module collects the project's SQLAlchemy models and attempts to
initialize and mount a Starlette-Admin instance at `/admin` when
`mount_admin(app)` is called from the application factory.

The Starlette-Admin API surface has varied between releases, so this
module performs imports and registrations defensively: if the installed
version exposes different names, the function will fail gracefully and
log an informational message rather than raising on import-time.
"""
from typing import List
import logging

# Import model classes to register with admin
from apps.user.models import UserModel, RefreshTokenModel
from apps.guest.models import GuestModel, GuestRefreshTokenModel
from apps.allocation.models import (
    TicketHolderModel,
    AllocationModel,
    AllocationTicketModel,
    AllocationEdgeModel,
    OrderModel,
)
from apps.ticketing.models import (
    TicketTypeModel,
    DayTicketAllocationModel,
    TicketModel,
)
from apps.organizer.models import OrganizerPageModel
from apps.superadmin.models import SuperAdminModel, B2BRequestModel
from apps.event.models import (
    EventModel,
    EventInterestModel,
    EventDayModel,
    ScanStatusHistoryModel,
    EventMediaAssetModel,
    EventResellerModel,
)
from apps.user.invite.models import InviteModel

LOG = logging.getLogger("project.admin")


def _collect_models() -> List[type]:
    """Return a list of model classes to register in the admin UI."""
    return [
        # user
        UserModel,
        RefreshTokenModel,
        # guest
        GuestModel,
        GuestRefreshTokenModel,
        # allocation
        TicketHolderModel,
        AllocationModel,
        AllocationTicketModel,
        AllocationEdgeModel,
        OrderModel,
        # ticketing
        TicketTypeModel,
        DayTicketAllocationModel,
        TicketModel,
        # organizer
        OrganizerPageModel,
        # superadmin
        SuperAdminModel,
        B2BRequestModel,
        # event
        EventModel,
        EventInterestModel,
        EventDayModel,
        ScanStatusHistoryModel,
        EventMediaAssetModel,
        EventResellerModel,
        # invites
        InviteModel,
    ]


def mount_admin(app) -> None:
    """Attempt to initialize and mount Starlette-Admin at `/admin`.

    This function will try to import common entry points from
    different `starlette-admin` versions and register models. If the
    runtime API doesn't match expectations the function will log an
    informational message and return without raising so the main app
    remains usable.
    """
    models = _collect_models()

    try:
        # Try the most common import path first
        from starlette_admin.site import Admin as StarletteAdmin  # type: ignore
    except Exception:
        try:
            # Fallback: some versions expose a top-level Admin
            from starlette_admin import Admin as StarletteAdmin  # type: ignore
        except Exception as exc:  # pragma: no cover - informative only
            LOG.info("starlette-admin not available or import path changed: %s", exc)
            return

    try:
        # Initialize admin. We try to be permissive in case Admin's
        # constructor requires different args; many versions accept no
        # args and return a mountable ASGI app / router.
        admin_instance = None
        try:
            admin_instance = StarletteAdmin()
        except TypeError:
            # Try to instantiate with a title argument as a fallback
            try:
                admin_instance = StarletteAdmin(title="Admin")
            except Exception as exc:  # pragma: no cover - informative only
                LOG.info("Unable to instantiate Starlette-Admin: %s", exc)
                return

        # Register models if the instance exposes a registration API.
        for model in models:
            try:
                if hasattr(admin_instance, "register_model"):
                    admin_instance.register_model(model)
                elif hasattr(admin_instance, "register"):
                    admin_instance.register(model)
                else:
                    # Some admin objects are already ASGI apps and expect
                    # model registration via separate helpers; skip in that
                    # case and rely on the user to customize further.
                    LOG.debug("Admin instance exposes no register method; skipping model registration")
                    break
            except Exception as exc:  # pragma: no cover - informative only
                LOG.info("Failed to register model %s: %s", getattr(model, "__name__", str(model)), exc)

        # Mount the admin instance at /admin if it's a Starlette/FastAPI
        # mountable object.
        try:
            app.mount("/admin", admin_instance)
            LOG.info("Mounted Starlette-Admin at /admin")
        except Exception as exc:  # pragma: no cover - informative only
            LOG.info("Starlette-Admin was created but could not be mounted automatically: %s", exc)
            LOG.info("You may need to mount the admin instance manually or adapt this helper for your starlette-admin version.")

    except Exception as exc:  # pragma: no cover - defensive
        LOG.info("Unexpected error while initializing admin: %s", exc)

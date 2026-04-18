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

    # Prefer the SQLAlchemy-backed Admin if available; it accepts an engine
    try:
        from starlette_admin.contrib.sqla.admin import Admin as SQLAAdmin  # type: ignore
        from starlette_admin.contrib.sqla.view import ModelView  # type: ignore
        # Import the project's SQLAlchemy engine
        from db.session import engine as db_engine

        try:
            admin = SQLAAdmin(db_engine)
        except Exception as exc:  # pragma: no cover - informative only
            LOG.info("Unable to instantiate SQLA Admin: %s", exc)
            admin = None

        # Register model views
        if admin is not None:
            for model in models:
                try:
                    view = ModelView(model)
                    admin.add_view(view)
                except Exception as exc:  # pragma: no cover - informative only
                    LOG.info("Failed to add view for model %s: %s", getattr(model, "__name__", str(model)), exc)

            try:
                # mount_to attaches admin into the Starlette app (creates routes)
                admin.mount_to(app)
                LOG.info("Mounted starlette-admin SQLA Admin at /admin")
            except Exception as exc:  # pragma: no cover - informative only
                LOG.info("SQLA Admin created but could not be mounted: %s", exc)
                return

        return
    except Exception as exc:  # pragma: no cover - try other options
        LOG.debug("SQLA Admin unavailable: %s", exc)

    # Fallbacks for other API surfaces
    try:
        from starlette_admin.base import BaseAdmin  # type: ignore

        try:
            admin = BaseAdmin()
            admin.mount_to(app)
            LOG.info("Mounted starlette-admin BaseAdmin at /admin")
        except Exception as exc:  # pragma: no cover - informative only
            LOG.info("BaseAdmin created but could not be mounted: %s", exc)
            return
    except Exception as exc:
        LOG.info("No compatible starlette-admin API found: %s", exc)
        return

from apps.event.enums import (
    AssetType,
    EventAccessType,
    EventStatus,
    EventType,
    LocationMode,
    ScanStatus,
    _to_options,
)
from apps.ticketing.enums import TicketCategoryPublic


class EnumService:
    def list_enums(self) -> dict[str, list[dict[str, str]]]:
        return {
            "asset_type": _to_options(AssetType),
            "event_type": _to_options(EventType),
            "event_status": _to_options(EventStatus),
            "event_access_type": _to_options(EventAccessType),
            "ticket_category": _to_options(TicketCategoryPublic),
            "location_mode": _to_options(LocationMode),
            "scan_status": _to_options(ScanStatus),
        }

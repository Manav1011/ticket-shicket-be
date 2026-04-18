from enum import Enum


def _to_options(enum_cls: type[Enum]) -> list[dict[str, str]]:
    return [
        {"value": member.value, "label": member.name.replace("_", " ").title()}
        for member in enum_cls
    ]


class AssetType(str, Enum):
    banner = "banner"
    gallery_image = "gallery_image"
    gallery_video = "gallery_video"
    promo_video = "promo_video"


class EventType(str, Enum):
    concert = "concert"
    conference = "conference"
    meetup = "meetup"
    workshop = "workshop"
    custom = "custom"


class EventStatus(str, Enum):
    draft = "draft"
    published = "published"
    archived = "archived"


class EventAccessType(str, Enum):
    open = "open"
    ticketed = "ticketed"


class LocationMode(str, Enum):
    venue = "venue"
    online = "online"
    recorded = "recorded"
    hybrid = "hybrid"


class ScanStatus(str, Enum):
    not_started = "not_started"
    active = "active"
    paused = "paused"
    ended = "ended"

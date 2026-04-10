from enum import Enum


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

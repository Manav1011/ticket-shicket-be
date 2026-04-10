from enum import Enum


class OrganizerVisibility(str, Enum):
    public = "public"
    private = "private"


class OrganizerStatus(str, Enum):
    active = "active"
    archived = "archived"

from dataclasses import dataclass
from typing import ClassVar
from datetime import timedelta


@dataclass
class StreamConfig:
    name: str
    subjects: list[str]
    retention: str = "limits"  # messages retained until consumed
    max_age: timedelta = timedelta(hours=1)
    max_bytes: int = 10 * 1024 * 1024  # 10MB — expiry messages are tiny
    storage: str = "file"


STREAMS: ClassVar[dict[str, StreamConfig]] = {
    "orders_expiry": StreamConfig(
        name="ORDERS_EXPIRY",
        subjects=["orders.expiry"],
        retention="limits",
        max_age=timedelta(hours=1),
        max_bytes=10 * 1024 * 1024,
    ),
}

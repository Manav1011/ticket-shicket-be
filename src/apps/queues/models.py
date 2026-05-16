import uuid
from typing import Self

from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, TimeStampMixin, UUIDPrimaryKeyMixin


class QueuesModel(Base, UUIDPrimaryKeyMixin, TimeStampMixin):
    __tablename__ = "queues"
    # define your fields here
    pass

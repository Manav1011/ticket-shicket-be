import uuid
from typing import Self

from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, TimeStampMixin, UUIDPrimaryKeyMixin


class AllocationModel(Base, UUIDPrimaryKeyMixin, TimeStampMixin):
    __tablename__ = "allocation"
    # define your fields here
    pass

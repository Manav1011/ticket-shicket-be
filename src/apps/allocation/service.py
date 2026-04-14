from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .repository import AllocationRepository


class AllocationService:
    def __init__(self, repository: "AllocationRepository") -> None:
        self.repository = repository

    # write your service methods here

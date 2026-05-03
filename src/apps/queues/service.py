from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .repository import QueuesRepository


class QueuesService:
    def __init__(self, repository: "QueuesRepository") -> None:
        self.repository = repository

    # write your service methods here

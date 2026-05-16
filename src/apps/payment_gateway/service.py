from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .repository import Payment_GatewayRepository


class Payment_GatewayService:
    def __init__(self, repository: "Payment_GatewayRepository") -> None:
        self.repository = repository

    # write your service methods here

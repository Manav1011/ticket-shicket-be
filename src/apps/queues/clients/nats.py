import logging
from typing import Optional
import nats
from nats.js.client import JetStreamContext

logger = logging.getLogger(__name__)


class NATSClient:
    """
    Singleton NATS client with Jetstream support.
    Reused across the app for publishing order events.
    """
    _instance: Optional["NATSClient"] = None
    _nc: Optional[nats.NATS] = None
    _js: Optional[JetStreamContext] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def connect(self, url: str = "nats://localhost:4222") -> nats.NATS:
        """Connect to NATS (idempotent — reuses existing connection)."""
        if self._nc is None or not self._nc.is_connected:
            self._nc = await nats.connect(url)
            self._js = self._nc.jetstream()
            logger.info(f"NATS connected to {url}")
        return self._nc

    @property
    def jetstream(self) -> JetStreamContext:
        if self._js is None:
            raise RuntimeError("NATS not connected. Call connect() first.")
        return self._js

    async def close(self):
        if self._nc:
            await self._nc.close()
            self._nc = None
            self._js = None

    async def publish_order_created(self, order_id: str):
        """
        Publish an order.created event to NATS for audit/tracing.
        The expiry worker does NOT consume this — it scans DB directly.
        """
        import json
        from apps.queues.config import STREAMS

        stream_cfg = STREAMS["orders_expiry"]
        await self.jetstream.publish(
            "orders.expiry",
            json.dumps({"order_id": order_id, "event": "order.created"}).encode(),
            stream=stream_cfg.name,
        )
        logger.debug(f"Published order.created for {order_id}")


async def get_nats_client() -> NATSClient:
    client = NATSClient()
    await client.connect()
    return client

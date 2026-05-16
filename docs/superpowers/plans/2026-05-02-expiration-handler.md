# Expiration Handler (Queues App) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `queues` app with NATS Jetstream for order expiry — NATS client for event publishing, and a scheduler-based expiry worker that uses SQLAlchemy repositories (following existing codebase patterns).

**Architecture:** The expiry worker is a **scheduler-based job** (not message-driven) that runs every 30 seconds. It uses `OrderExpiryRepository` (SQLAlchemy async) to perform a bulk atomic UPDATE with RETURNING on orders past their `lock_expires_at`. Indexes are defined in models, not migrations.

**Why not message-driven expiry?** NATS `NATS-Deliver-Time` headers don't work reliably in this client version. A scheduled bulk scan is simpler, faster (single query for all expirations), and has deterministic latency (max 30s from expiry time).

**Tech Stack:** `nats-py` (async), SQLAlchemy async, existing models/repositories, NATS Jetstream.

---

## ⚠️ Pre-requisites: OrderModel Payment Fields (MUST be done first)

The expiry worker depends on `OrderModel` having payment fields that **do not exist yet**. These must be added before the `OrderExpiryRepository` can be implemented or tests can pass.

### Pre-requisite A: Add payment fields to OrderModel

**File:** `src/apps/allocation/models.py` — add to `OrderModel`

```python
# After existing OrderModel fields, add:

    payment_gateway: Mapped[str | None] = mapped_column(
        String(32), nullable=True, index=True
    )  # "razorpay", "stripe"
    gateway_type: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )  # "razorpay_order" | "razorpay_payment_link"
    gateway_order_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, unique=True, index=True
    )  # Razorpay order_id OR payment_link id
    gateway_response: Mapped[dict] = mapped_column(
        JSONB, default=dict, server_default=text("'{}'::jsonb"), nullable=False
    )  # Full gateway response on creation
    short_url: Mapped[str | None] = mapped_column(
        String(512), nullable=True
    )  # Payment link short_url (for payment_link type only)
    gateway_payment_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )  # razorpay payment_id (set after capture)
    lock_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

**Also add to `__table_args__` of OrderModel:**

```python
    __table_args__ = (
        Index(
            "ix_orders_status_lock_expires_at",
            "status", "lock_expires_at",
            postgresql_where=text("lock_expires_at IS NOT NULL"),
        ),
    )
```

**Generate migration:**
```bash
uv run main.py makemigrations --name add_payment_fields_to_orders
```

---

### Pre-requisite B: Add GatewayType enum

**File:** `src/apps/allocation/enums.py`

Add at end of file:

```python
class GatewayType(str, Enum):
    RAZORPAY_ORDER = "razorpay_order"          # Checkout flow (online purchase, V2)
    RAZORPAY_PAYMENT_LINK = "razorpay_payment_link"  # Payment link flow (B2B)
    STRIPE_CHECKOUT = "stripe_checkout"       # Future
```

**Apply migration:**
```bash
uv run main.py migrate
```

---

### Pre-requisite C: Add unique constraint on allocations.order_id

**File:** `src/apps/allocation/models.py` — add to `AllocationModel.__table_args__`

```python
UniqueConstraint("order_id", name="uq_allocations_order_id"),
```

**Generate migration:**
```bash
uv run main.py makemigrations --name add_order_id_unique_to_allocations
uv run main.py migrate
```

---

## File Structure

```
src/apps/queues/
├── __init__.py                     # App export
├── config.py                       # Stream definitions
├── repository.py                   # OrderExpiryRepository
├── clients/
│   ├── __init__.py
│   └── nats.py                    # NATS client singleton + publish_order_created()
└── workers/
    ├── __init__.py
    └── expiry.py                   # ExpiryWorker (scheduler-based, every 30s)

src/apps/allocation/
├── enums.py                        # GatewayType enum (Pre-requisite B)
└── models.py                       # Payment fields + indexes (Pre-requisite A)

scripts/
└── run_expiry_worker.py            # Entry point: python scripts/run_expiry_worker.py
```

---

## Task 1: Create `queues` App Structure (after Pre-requisites A, B, C are done)

**Files:**
- Create: `src/apps/queues/__init__.py`
- Create: `src/apps/queues/config.py`
- Create: `src/apps/queues/repository.py` — `OrderExpiryRepository`
- Create: `src/apps/queues/clients/__init__.py`
- Create: `src/apps/queues/clients/nats.py` — NATS client singleton + `publish_order_created()`
- Create: `src/apps/queues/workers/__init__.py`
- Create: `src/apps/queues/workers/expiry.py` — scheduler-based (every 30s)
- Create: `scripts/run_expiry_worker.py`

---

- [ ] **Step 1: Create `src/apps/queues/config.py`**

```python
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
```

---

- [ ] **Step 2: Create `src/apps/queues/clients/nats.py`**

```python
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
```

---

- [ ] **Step 3: Create `src/apps/queues/clients/__init__.py`**

```python
from apps.queues.clients.nats import NATSClient, get_nats_client

__all__ = ["NATSClient", "get_nats_client"]
```

---

- [ ] **Step 4: Create `src/apps/queues/__init__.py`**

```python
from apps.queues.config import STREAMS
from apps.queues.clients.nats import NATSClient, get_nats_client
from apps.queues.repository import OrderExpiryRepository

__all__ = ["STREAMS", "NATSClient", "get_nats_client", "OrderExpiryRepository"]
```

---

- [ ] **Step 5: Create `src/apps/queues/repository.py`**

```python
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from apps.allocation.enums import OrderStatus
from apps.allocation.models import OrderModel
from apps.ticketing.models import TicketModel


class OrderExpiryRepository:
    """
    Repository for order expiry operations.
    Used by the scheduler-based expiry worker (ExpiryWorker).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

    async def bulk_expire_pending_orders(self) -> list[dict]:
        """
        Bulk expire all pending orders past their lock_expires_at.

        Returns:
            List of dicts: [{"id": UUID, "gateway_type": str, "gateway_order_id": str}, ...]
        """
        stmt = (
            update(OrderModel)
            .where(
                OrderModel.status == OrderStatus.pending,
                OrderModel.lock_expires_at.is_not(None),
                OrderModel.lock_expires_at < datetime.utcnow(),
            )
            .values(
                status=OrderStatus.expired,
                expired_at=datetime.utcnow(timezone.utc),
            )
            .returning(OrderModel.id, OrderModel.gateway_type, OrderModel.gateway_order_id)
        )
        result = await self._session.execute(stmt)
        rows = result.fetchall()
        return [
            {
                "id": row.id,
                "gateway_type": row.gateway_type,
                "gateway_order_id": row.gateway_order_id,
            }
            for row in rows
        ]

    async def clear_ticket_locks(self, order_id: UUID) -> int:
        """
        Clear all ticket locks for an expired order.
        Uses lock_reference_type='order' and lock_reference_id=order_id.
        Returns number of tickets unlocked.
        """
        stmt = (
            update(TicketModel)
            .where(
                TicketModel.lock_reference_id == order_id,
                TicketModel.lock_reference_type == "order",
            )
            .values(
                lock_reference_type=None,
                lock_reference_id=None,
                lock_expires_at=None,
            )
        )
        result = await self._session.execute(stmt)
        return result.rowcount
```

---

- [ ] **Step 6: Create `src/apps/queues/workers/__init__.py`**

```python
from apps.queues.workers.expiry import ExpiryWorker

__all__ = ["ExpiryWorker"]
```

---

- [ ] **Step 7: Create `src/apps/queues/workers/expiry.py`**

```python
import asyncio
import logging
from datetime import datetime, timezone

from apps.allocation.enums import GatewayType


logger = logging.getLogger(__name__)

# Interval between expiry scans
EXPIRY_SCAN_INTERVAL = 30  # seconds


class ExpiryWorker:
    """
    Scheduler-based expiry worker that runs every 30 seconds.

    Flow:
      1. OrderExpiryRepository.bulk_expire_pending_orders() — single UPDATE with RETURNING
      2. For each expired order: clear locks via repository, cancel payment link (fire-and-forget)
      3. Log results

    NOT message-driven — runs on a timer and uses SQLAlchemy repositories.
    """

    def __init__(self):
        self._running = False

    async def start(self):
        self._running = True
        logger.info("Expiry worker started (interval=30s)")

        while self._running:
            try:
                await self._run_expiry_scan()
            except Exception as e:
                logger.error(f"Expiry scan error: {e}")
            await asyncio.sleep(EXPIRY_SCAN_INTERVAL)

    async def stop(self):
        self._running = False
        logger.info("Expiry worker stopped")

    async def _run_expiry_scan(self):
        """Bulk expire all pending orders past their lock time."""
        from src.db.session import async_session
        from apps.queues.repository import OrderExpiryRepository

        async with async_session() as session:
            repo = OrderExpiryRepository(session)
            expired_orders = await repo.bulk_expire_pending_orders()
            await session.commit()

        if not expired_orders:
            logger.debug("No orders to expire")
            return

        logger.info(f"Bulk expired {len(expired_orders)} orders")

        for order in expired_orders:
            asyncio.create_task(self._handle_expired_order(order))

    async def _handle_expired_order(self, order: dict):
        """Clear locks and cancel payment link for one expired order."""
        from src.db.session import async_session
        from apps.queues.repository import OrderExpiryRepository

        async with async_session() as session:
            repo = OrderExpiryRepository(session)
            unlocked = await repo.clear_ticket_locks(order["id"])
            await session.commit()
            logger.debug(f"Unlocked {unlocked} tickets for order {order['id']}")

        if order["gateway_type"] == GatewayType.RAZORPAY_PAYMENT_LINK.value:
            if order["gateway_order_id"]:
                asyncio.create_task(
                    self._cancel_payment_link(order["gateway_order_id"])
                )

        logger.info(f"Expired order {order['id']} processed")

    async def _cancel_payment_link(self, gateway_order_id: str):
        """Cancel Razorpay payment link — fire and forget, retry with backoff."""
        if not gateway_order_id:
            return
        try:
            from apps.payment_gateway.services.factory import get_gateway
            gateway = get_gateway("razorpay")
            await gateway.cancel_payment_link_with_retry(gateway_order_id, max_retries=3)
        except Exception as e:
            logger.error(f"Failed to cancel payment link {gateway_order_id}: {e}")


async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    worker = ExpiryWorker()
    await worker.start()


if __name__ == "__main__":
    asyncio.run(main())
```

---

- [ ] **Step 8: Create `scripts/run_expiry_worker.py`**

```python
#!/usr/bin/env python3
"""Entry point for expiry worker — run via systemd/supervisor."""
import asyncio
import logging
from src.apps.queues.workers.expiry import main

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )
    asyncio.run(main())
```

Run: `chmod +x scripts/run_expiry_worker.py`

---

- [ ] **Step 9: Write test for expiry worker**

Create: `tests/apps/queues/test_expiry_worker.py`

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from apps.queues.workers.expiry import ExpiryWorker, EXPIRY_SCAN_INTERVAL


class TestExpiryWorker:
    """Unit tests for ExpiryWorker._run_expiry_scan and _handle_expired_order."""

    @pytest.fixture
    def worker(self):
        return ExpiryWorker()

    @pytest.mark.asyncio
    async def test_bulk_expire_skips_when_no_orders(self, worker):
        """When no orders are past expiry, nothing is logged as expired."""
        mock_repo = AsyncMock()
        mock_repo.bulk_expire_pending_orders.return_value = []

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        with patch("apps.queues.workers.expiry.async_session") as mock_async_session:
            mock_async_session.return_value.__aenter__.return_value = mock_session
            with patch("apps.queues.workers.expiry.OrderExpiryRepository", return_value=mock_repo):
                await worker._run_expiry_scan()

        mock_repo.bulk_expire_pending_orders.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_expire_logs_when_orders_found(self, worker):
        """When orders are found, _handle_expired_order is called for each."""
        order_uuid = uuid4()
        mock_repo = AsyncMock()
        mock_repo.bulk_expire_pending_orders.return_value = [
            {"id": order_uuid, "gateway_type": "razorpay_payment_link", "gateway_order_id": "plink_abc"}
        ]

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        with patch("apps.queues.workers.expiry.async_session") as mock_async_session:
            mock_async_session.return_value.__aenter__.return_value = mock_session
            with patch("apps.queues.workers.expiry.OrderExpiryRepository", return_value=mock_repo):
                with patch.object(worker, "_handle_expired_order", new_callable=AsyncMock) as mock_handle:
                    await worker._run_expiry_scan()

        mock_handle.assert_called_once()
        call_args = mock_handle.call_args[0][0]
        assert call_args["id"] == order_uuid
        assert call_args["gateway_type"] == "razorpay_payment_link"

    @pytest.mark.asyncio
    async def test_expired_order_clears_locks_and_cancels_payment_link(self, worker):
        """Order with razorpay_payment_link gets lock clear + cancel call."""
        order = {
            "id": uuid4(),
            "gateway_type": "razorpay_payment_link",
            "gateway_order_id": "plink_abc",
        }

        mock_repo = AsyncMock()
        mock_repo.clear_ticket_locks.return_value = 5

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        with patch("apps.queues.workers.expiry.async_session") as mock_async_session:
            mock_async_session.return_value.__aenter__.return_value = mock_session
            with patch("apps.queues.workers.expiry.OrderExpiryRepository", return_value=mock_repo):
                with patch.object(worker, "_cancel_payment_link", new_callable=AsyncMock) as mock_cancel:
                    await worker._handle_expired_order(order)

        mock_repo.clear_ticket_locks.assert_called_once_with(order["id"])
        mock_cancel.assert_called_once_with("plink_abc")

    @pytest.mark.asyncio
    async def test_expired_order_no_cancel_for_checkout_type(self, worker):
        """Order with razorpay_order type does NOT call payment link cancel."""
        order = {
            "id": uuid4(),
            "gateway_type": "razorpay_order",
            "gateway_order_id": "order_xyz",
        }

        mock_repo = AsyncMock()
        mock_repo.clear_ticket_locks.return_value = 3

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        with patch("apps.queues.workers.expiry.async_session") as mock_async_session:
            mock_async_session.return_value.__aenter__.return_value = mock_session
            with patch("apps.queues.workers.expiry.OrderExpiryRepository", return_value=mock_repo):
                with patch.object(worker, "_cancel_payment_link", new_callable=AsyncMock) as mock_cancel:
                    await worker._handle_expired_order(order)

        mock_repo.clear_ticket_locks.assert_called_once()
        mock_cancel.assert_not_called()


class TestOrderExpiryRepository:
    """Unit tests for OrderExpiryRepository methods."""

    @pytest.mark.asyncio
    async def test_bulk_expire_pending_orders_returns_list(self):
        """Verify bulk_expire_pending_orders returns correct shape."""
        from apps.queues.repository import OrderExpiryRepository

        order_uuid = uuid4()
        mock_row = MagicMock()
        mock_row.id = order_uuid
        mock_row.gateway_type = "razorpay_payment_link"
        mock_row.gateway_order_id = "plink_abc"

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [mock_row]

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result

        repo = OrderExpiryRepository(mock_session)
        result = await repo.bulk_expire_pending_orders()

        assert len(result) == 1
        assert result[0]["id"] == order_uuid
        assert result[0]["gateway_type"] == "razorpay_payment_link"

    @pytest.mark.asyncio
    async def test_clear_ticket_locks_returns_rowcount(self):
        """Verify clear_ticket_locks returns the number of updated rows."""
        from apps.queues.repository import OrderExpiryRepository

        mock_result = MagicMock()
        mock_result.rowcount = 5

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result

        repo = OrderExpiryRepository(mock_session)
        result = await repo.clear_ticket_locks(uuid4())

        assert result == 5


class TestExpiryWorkerInterval:
    """Test worker interval configuration."""

    def test_expiry_scan_interval_is_30_seconds(self):
        assert EXPIRY_SCAN_INTERVAL == 30


class TestStreamConfig:
    """Tests for stream configuration."""

    def test_stream_config_has_correct_name(self):
        from apps.queues.config import STREAMS
        assert STREAMS["orders_expiry"].name == "ORDERS_EXPIRY"

    def test_stream_config_limits_retention(self):
        from apps.queues.config import STREAMS
        assert STREAMS["orders_expiry"].retention == "limits"

    def test_stream_config_max_age_1_hour(self):
        from apps.queues.config import STREAMS
        from datetime import timedelta
        assert STREAMS["orders_expiry"].max_age == timedelta(hours=1)
```

---

- [ ] **Step 10: Run tests to verify they pass**

Run: `uv run pytest tests/apps/queues/test_expiry_worker.py -v`
Expected: All 10 tests pass

---

- [ ] **Step 11: Commit**

```bash
git add src/apps/queues/ scripts/run_expiry_worker.py
git add src/apps/allocation/models.py src/apps/allocation/enums.py  # payment fields + GatewayType
git add tests/apps/queues/test_expiry_worker.py
git commit -m "feat(queues): add expiration handler with scheduler-based worker

Pre-requisites:
- Add payment fields to OrderModel (lock_expires_at, gateway_type, etc.)
- Add GatewayType enum to allocation/enums.py
- Add unique constraint on allocations.order_id

- Add queues app with NATS client singleton + config
- ExpiryWorker runs every 30s, uses OrderExpiryRepository
- bulk_expire_pending_orders: single UPDATE with RETURNING
- clear_ticket_locks: clears order-based locks on tickets
- Fire-and-forget payment link cancellation per expired order"
```

---

## How to Continue

After Task 1 is done, update `docs/sprint-planning/2026-05-02-payments-progress.md` to mark expiration handling as complete, then move to the payment gateway implementation.

---

*Last updated: 2026-05-03*
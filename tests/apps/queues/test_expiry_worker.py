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
        from apps.queues.repository import OrderExpiryRepository

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_repo = AsyncMock()
        mock_repo.bulk_expire_pending_orders.return_value = []

        with patch("apps.queues.workers.expiry.async_session") as mock_async_session:
            mock_async_session.return_value.__aenter__.return_value = mock_session
            with patch("apps.queues.workers.expiry.OrderExpiryRepository", return_value=mock_repo):
                await worker._run_expiry_scan()

        mock_repo.bulk_expire_pending_orders.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_expire_logs_when_orders_found(self, worker):
        """When orders are found, _handle_expired_order is called for each."""
        order_uuid = str(uuid4())
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
    async def test_expired_order_clears_locks(self, worker):
        """Order with razorpay_payment_link gets lock clear (cancel link commented out for now)."""
        order = {
            "id": str(uuid4()),
            "gateway_type": "razorpay_payment_link",
            "gateway_order_id": "plink_abc",
        }

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_repo = AsyncMock()
        mock_repo.clear_ticket_locks.return_value = 5

        with patch("apps.queues.workers.expiry.async_session") as mock_async_session:
            mock_async_session.return_value.__aenter__.return_value = mock_session
            with patch("apps.queues.workers.expiry.OrderExpiryRepository", return_value=mock_repo):
                await worker._handle_expired_order(order)

        mock_repo.clear_ticket_locks.assert_called_once()

    @pytest.mark.asyncio
    async def test_expired_order_clears_locks_for_checkout_type(self, worker):
        """Order with razorpay_order type clears locks (cancel link commented out for now)."""
        order = {
            "id": str(uuid4()),
            "gateway_type": "razorpay_order",
            "gateway_order_id": "order_xyz",
        }

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_repo = AsyncMock()
        mock_repo.clear_ticket_locks.return_value = 3

        with patch("apps.queues.workers.expiry.async_session") as mock_async_session:
            mock_async_session.return_value.__aenter__.return_value = mock_session
            with patch("apps.queues.workers.expiry.OrderExpiryRepository", return_value=mock_repo):
                await worker._handle_expired_order(order)

        mock_repo.clear_ticket_locks.assert_called_once()


class TestOrderExpiryRepository:
    """Unit tests for OrderExpiryRepository methods."""

    @pytest.mark.asyncio
    async def test_bulk_expire_pending_orders_returns_list(self):
        """Verify bulk_expire_pending_orders returns correct shape."""
        from apps.queues.repository import OrderExpiryRepository

        mock_row = MagicMock()
        mock_row.id = uuid4()
        mock_row.gateway_type = "razorpay_payment_link"
        mock_row.gateway_order_id = "plink_abc"

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [mock_row]

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result

        repo = OrderExpiryRepository(mock_session)
        result = await repo.bulk_expire_pending_orders()

        assert len(result) == 1
        assert result[0]["id"] == mock_row.id
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

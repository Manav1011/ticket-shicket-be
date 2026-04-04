import pytest
from unittest.mock import AsyncMock, MagicMock
from auth.blocklist import TokenBlocklist


@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    # pipeline() is NOT async, so override with a MagicMock that returns a sync pipe
    pipe = MagicMock()
    pipe.execute = AsyncMock(return_value=None)
    redis.pipeline = MagicMock(return_value=pipe)
    return redis


@pytest.fixture
def blocklist(mock_redis):
    return TokenBlocklist(redis=mock_redis)


@pytest.mark.asyncio
async def test_add_jti_to_blocklist(blocklist, mock_redis):
    """Adding a jti should add it to the Redis set."""
    jti = "test-jti-123"
    await blocklist.add(jti)
    mock_redis.pipeline.return_value.sadd.assert_called_once_with("token_blocklist", jti)


@pytest.mark.asyncio
async def test_is_jti_blocklisted_true(blocklist, mock_redis):
    """Blocked jti should return True."""
    mock_redis.sismember.return_value = True
    result = await blocklist.is_blocklisted("blocked-jti")
    assert result is True
    mock_redis.sismember.assert_called_once_with("token_blocklist", "blocked-jti")


@pytest.mark.asyncio
async def test_is_jti_blocklisted_false(blocklist, mock_redis):
    """Non-blocklisted jti should return False."""
    mock_redis.sismember.return_value = False
    result = await blocklist.is_blocklisted("valid-jti")
    assert result is False


@pytest.mark.asyncio
async def test_add_jti_with_ttl(blocklist, mock_redis):
    """Adding a jti with TTL should also set expiry on the set."""
    mock_pipe = AsyncMock()
    mock_redis.pipeline.return_value = mock_pipe
    mock_pipe.sadd.return_value = mock_pipe
    mock_pipe.expire.return_value = mock_pipe
    mock_pipe.execute.return_value = None

    await blocklist.add("test-jti", ttl=3600)
    mock_pipe.sadd.assert_called_once_with("token_blocklist", "test-jti")
    mock_pipe.expire.assert_called_once_with("token_blocklist", 3600)
    mock_pipe.execute.assert_called_once()


@pytest.mark.asyncio
async def test_remove_jti_from_blocklist(blocklist, mock_redis):
    """Removing a jti should remove it from the Redis set."""
    jti = "test-jti-456"
    await blocklist.remove(jti)
    mock_redis.srem.assert_called_once_with("token_blocklist", jti)
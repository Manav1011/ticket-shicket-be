"""
Redis-based token blocklist for invalidating access tokens.

Uses a Redis SET to store blocked JTIs (JWT IDs). Access tokens
carry a `jti` claim; on logout, the jti is added to this set.
Every authenticated request checks is_blocklisted(jti) before proceeding.
"""

from redis.asyncio import Redis


class TokenBlocklist:
    """
    Manages a Redis SET of blocked token JTIs.
    """

    KEY = "token_blocklist"

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def add(self, jti: str, *, ttl: int | None = None) -> None:
        """
        Add a jti to the blocklist.
        Optionally set a TTL (in seconds) to auto-expire the blocklist entry.
        If ttl is None, the entry stays until explicitly removed.
        """
        pipe = self._redis.pipeline()
        pipe.sadd(self.KEY, jti)
        if ttl is not None:
            # Set expiry on the set itself (approximate — set members don't have individual TTL)
            pipe.expire(self.KEY, ttl)
        await pipe.execute()

    async def is_blocklisted(self, jti: str) -> bool:
        """Check if a jti is in the blocklist."""
        return await self._redis.sismember(self.KEY, jti)

    async def remove(self, jti: str) -> None:
        """Remove a jti from the blocklist (not typically needed)."""
        await self._redis.srem(self.KEY, jti)
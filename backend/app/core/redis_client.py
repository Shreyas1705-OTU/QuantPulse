"""
Shared Redis connections for the backend.

Two clients, because the two consumers need different flavors:

- `redis_client` (sync) -- used by app/core/cache.py inside ordinary
  request handlers, which are themselves sync (SQLAlchemy's Session is
  sync, so the routers that call it are too).
- `get_async_redis()` (async) -- used by app/routers/stream.py's
  WebSocket relay, which needs to await pubsub messages without blocking
  the event loop while waiting for the next one.

Both are lazy: redis-py only opens a connection on the first real command,
so importing this module never itself requires Redis to be up.
"""

import redis
import redis.asyncio as redis_asyncio

from app.core.config import settings

# Short timeouts so a hung/unreachable Redis degrades a cache-aside read
# into "just hit Postgres" (see app/core/cache.py) rather than stalling
# the request.
redis_client = redis.Redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=2,
)


def get_async_redis() -> redis_asyncio.Redis:
    # A fresh connection per call rather than one shared client -- the
    # WebSocket relay holds this open for the lifetime of a single
    # connection (potentially hours), so it gets its own rather than
    # sharing a pool with short-lived cache reads.
    #
    # Same socket timeouts as the sync client above, for the same reason:
    # without them, a silent network partition to Redis (as opposed to a
    # clean connection refusal) leaves the underlying TCP connect retrying
    # for minutes with nothing to interrupt it, hanging pubsub.subscribe/
    # unsubscribe/close indefinitely and leaking a connection + asyncio
    # task per stuck WebSocket.
    return redis_asyncio.Redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )

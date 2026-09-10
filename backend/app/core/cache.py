"""
Cache-aside helpers for hot read endpoints (app/routers/ticks.py,
app/routers/summary.py).

Pure TTL expiry, not event-driven invalidation: a cached value is simply
overwritten with a fresh one on the next miss after it expires, whether
or not the underlying data actually changed. Deliberately simple --
correct enough here because every cached endpoint is read-heavy and
tolerates a few seconds of staleness (see each call site's TTL for how
much).

Every function is a no-op passthrough on a Redis error (connection
refused, timeout, ...) -- a cache outage must degrade to "always hit
Postgres, like before this existed", never take the endpoint down.
"""

import json

import redis

from app.core.redis_client import redis_client


def cache_get(key: str):
    try:
        raw = redis_client.get(key)
    except redis.RedisError:
        return None

    if raw is None:
        return None

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # A poisoned/malformed value (key collision with something else
        # written to this DB, a crashed cache_set, ...) must degrade to
        # "just hit Postgres" same as a Redis error would -- an uncaught
        # JSONDecodeError here would otherwise crash the request instead,
        # the opposite of what this module exists to guarantee. Delete it
        # so the next read doesn't hit the same decode error again before
        # its TTL naturally expires.
        try:
            redis_client.delete(key)
        except redis.RedisError:
            pass
        return None


def cache_set(key: str, value, ttl_seconds: int):
    try:
        redis_client.set(key, json.dumps(value, default=str), ex=ttl_seconds)
    except redis.RedisError:
        pass

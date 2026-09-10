"""
Live push relay: WS /api/v1/stream.

ingestion (finnhub_ingestion.py) publishes each tick/alert to Redis right
after writing it to Postgres. This endpoint is the other end of that:
one long-lived WebSocket connection per browser tab, subscribed to the
same Redis channels, relaying each message down to the client the moment
it arrives -- what lets the dashboard drop its old 5s poll in favor of
updating only when something actually happened.

Auth doesn't go through the usual Depends(get_current_user) path -- a
browser's native WebSocket API can't set an Authorization header on the
handshake request, unlike a normal fetch/XHR call. Instead: the
connection is accepted first, then the client's first text frame must be
{"token": "<jwt>"}, validated with the exact same decode + user lookup
every REST endpoint uses (get_user_from_token). Anything else --
timeout, malformed frame, bad/expired token -- closes the connection
with a 4401 (app-defined WS close code in the 4000-4999 range reserved
for that) rather than ever subscribing to Redis for an unauthenticated
caller. Unlike a REST call, though, a WS connection can sit open for
hours -- so that same check also re-runs every REAUTH_INTERVAL_SECONDS
for the life of the connection, not just once at handshake (see
_validate_token/REAUTH_INTERVAL_SECONDS below).
"""

import asyncio
import json
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from redis import RedisError
from starlette.concurrency import run_in_threadpool

from app.core.redis_client import get_async_redis
from app.core.security import get_user_from_token
from app.database.session import SessionLocal

router = APIRouter(tags=["Stream"])

CHANNELS = ["ticks", "alerts"]
AUTH_TIMEOUT_SECONDS = 10

# How long to wait for a Redis message before sending a keepalive ping
# instead. Below nginx's default proxy idle timeouts (and the ingress's)
# so a quiet market (nothing traded in a while) never looks like a dead
# connection to anything proxying this.
KEEPALIVE_SECONDS = 15

# Re-checked on this cadence for the life of the connection (see the main
# loop below) -- without this, a JWT valid at connect time keeps
# streaming forever, even past its own 60-minute expiry or past an admin
# deactivating the user, since a WS connection has no per-request auth
# check the way every REST endpoint does.
REAUTH_INTERVAL_SECONDS = 60


def _validate_token(token):
    """
    Sync JWT decode + user lookup (get_user_from_token does a blocking
    psycopg2 round-trip) -- every caller below runs this via
    run_in_threadpool, never awaits it directly. Awaiting a sync DB call
    straight from an async def would block the whole event loop for its
    duration, stalling every OTHER currently-open WS connection's relay
    and keepalives for as long as this one query takes.
    """
    db = SessionLocal()
    try:
        return get_user_from_token(token, db)
    finally:
        db.close()


async def _authenticate(websocket: WebSocket):
    """First frame must be {"token": "..."}; returns (user, token), (None, None) on failure."""
    try:
        first_message = await asyncio.wait_for(
            websocket.receive_text(), timeout=AUTH_TIMEOUT_SECONDS
        )
    except (asyncio.TimeoutError, WebSocketDisconnect):
        return None, None

    try:
        token = json.loads(first_message).get("token")
    except (json.JSONDecodeError, AttributeError):
        token = None

    if not token:
        return None, None

    user = await run_in_threadpool(_validate_token, token)
    return user, token


@router.websocket("/stream")
async def stream_events(websocket: WebSocket):
    await websocket.accept()

    user, token = await _authenticate(websocket)
    if user is None:
        await websocket.close(code=4401, reason="Unauthorized")
        return

    redis_conn = get_async_redis()
    pubsub = redis_conn.pubsub()

    try:
        await pubsub.subscribe(*CHANNELS)

        last_reauth = time.monotonic()

        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=KEEPALIVE_SECONDS,
            )

            if message is not None:
                # Already a JSON string -- publish_event() in
                # finnhub_ingestion.py json.dumps'd it before publishing,
                # so this is a straight passthrough, not a re-encode.
                await websocket.send_text(message["data"])
            else:
                await websocket.send_json({"type": "ping"})

            if time.monotonic() - last_reauth >= REAUTH_INTERVAL_SECONDS:
                last_reauth = time.monotonic()
                if await run_in_threadpool(_validate_token, token) is None:
                    await websocket.close(code=4401, reason="Session expired")
                    return

    except (WebSocketDisconnect, RedisError):
        # Client closed the tab, or Redis dropped mid-stream -- either
        # way there's nothing left to relay to. Not an error worth
        # logging loudly; the client's own reconnect logic (if any)
        # handles picking back up.
        pass

    finally:
        # Each cleanup call guarded independently -- if Redis died
        # mid-stream (the except above already caught that from
        # get_message), unsubscribe/close below would otherwise re-raise
        # the same RedisError trying to send commands over the same dead
        # connection, escaping this finally block as an unhandled
        # exception and skipping whichever cleanup call came after it.
        try:
            await pubsub.unsubscribe(*CHANNELS)
        except RedisError:
            pass

        try:
            await pubsub.close()
        except RedisError:
            pass

        try:
            await redis_conn.close()
        except RedisError:
            pass

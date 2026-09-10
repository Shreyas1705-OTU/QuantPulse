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
caller.
"""

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from redis import RedisError

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


async def _authenticate(websocket: WebSocket):
    """First frame must be {"token": "..."}; returns the User or None."""
    try:
        first_message = await asyncio.wait_for(
            websocket.receive_text(), timeout=AUTH_TIMEOUT_SECONDS
        )
    except (asyncio.TimeoutError, WebSocketDisconnect):
        return None

    try:
        token = json.loads(first_message).get("token")
    except (json.JSONDecodeError, AttributeError):
        token = None

    if not token:
        return None

    db = SessionLocal()
    try:
        return get_user_from_token(token, db)
    finally:
        db.close()


@router.websocket("/stream")
async def stream_events(websocket: WebSocket):
    await websocket.accept()

    user = await _authenticate(websocket)
    if user is None:
        await websocket.close(code=4401, reason="Unauthorized")
        return

    redis_conn = get_async_redis()
    pubsub = redis_conn.pubsub()

    try:
        await pubsub.subscribe(*CHANNELS)

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

    except (WebSocketDisconnect, RedisError):
        # Client closed the tab, or Redis dropped mid-stream -- either
        # way there's nothing left to relay to. Not an error worth
        # logging loudly; the client's own reconnect logic (if any)
        # handles picking back up.
        pass

    finally:
        await pubsub.unsubscribe(*CHANNELS)
        await pubsub.close()
        await redis_conn.close()

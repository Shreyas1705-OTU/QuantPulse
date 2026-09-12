"""
QuantPulse Finnhub ingestion service.

Connects to Finnhub's WebSocket, subscribes to every active symbol in
the `symbols` table, and writes each trade as a row in `ticks`. Runs as
a long-lived worker process -- separate from the FastAPI backend, its
own Dockerfile/deployment (see k8s/ingestion/). Writes directly to
Postgres via SQLAlchemy Core (reflecting the existing tables rather than
duplicating column definitions), not through the backend's API.

Exposes its own /metrics endpoint on :8001 -- this is the real place
"ticks ingested" (and, now, "alerts generated") belongs, since the backend
never touches these writes -- see anomaly_detector.py for the rolling
z-score check run on every tick.

Also publishes each tick/alert to Redis (see publish_event) right after
its Postgres write -- best-effort, non-fatal on failure, purely so the
backend's WS relay can push it live if anything's listening. Redis is
never the source of truth here and this process never reads from it.

MUST run as a single replica -- see k8s/ingestion/deployment.yaml.
"""

import json
import os
import time
from datetime import datetime, timezone

import redis
import websocket
from prometheus_client import Counter, start_http_server
from sqlalchemy import create_engine, MetaData, select

from anomaly_detector import AnomalyDetector

DATABASE_URL = os.environ["DATABASE_URL"]
FINNHUB_API_KEY = os.environ["FINNHUB_API_KEY"]

# Not a hard requirement like DATABASE_URL/FINNHUB_API_KEY above -- publish
# is best-effort (see publish_event below), so a missing/unreachable Redis
# degrades to "no live push", not "ingestion won't start". Default matches
# the in-cluster service name (k8s/redis/service.yaml) and docker-compose.
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")

TICKS_INGESTED_TOTAL = Counter(
    "quantpulse_ticks_ingested_total",
    "Total market ticks ingested from Finnhub",
)

# Moved here from backend/app/core/metrics.py -- the backend has no code
# path that ever creates an Alert (no POST /alerts route), so that counter
# could never fire. Real alerts are only ever created here, by the
# anomaly detector, so this is the real place for the metric.
#
# Labeled by severity -- Phase 3's Grafana dashboard breaks this down as
# HIGH vs MEDIUM, which an unlabeled total can't answer (see
# detector.check_tick's severity values in anomaly_detector.py).
ALERTS_TOTAL = Counter(
    "quantpulse_alerts_total",
    "Total alerts generated",
    ["severity"],
)

engine = create_engine(DATABASE_URL)
detector = AnomalyDetector()

# Short timeouts + decode_responses so publish() never blocks the tick loop
# waiting on a hung/unreachable Redis, and payloads round-trip as str, not
# bytes. Connection itself is lazy (redis-py only dials on first command),
# so a Redis that isn't up yet at process start doesn't delay startup --
# it just fails the first publish_event call, which is caught below.
redis_client = redis.Redis.from_url(
    REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=2,
)


# Circuit breaker for publish_event below. Without it, a Redis outage
# doesn't just fail each publish -- it costs the full socket_connect_timeout
# (2s) on EVERY publish attempt, and on_message calls publish_event once
# per trade inside its own loop, so a single batched Finnhub message with
# a few dozen trades could stall the tick-ingestion callback thread for
# tens of seconds, long enough for Finnhub to time out the connection.
# That directly contradicts publish_event's own "never blocks the tick
# loop" intent. After PUBLISH_FAILURE_THRESHOLD consecutive failures,
# publishes short-circuit for PUBLISH_COOLDOWN_SECONDS instead of paying
# the timeout again on every call.
_publish_state = {"failures": 0, "cooldown_until": 0.0}
PUBLISH_FAILURE_THRESHOLD = 3
PUBLISH_COOLDOWN_SECONDS = 10


def publish_event(channel, payload):
    """
    Best-effort publish to Redis -- a subscriber (the backend's WS relay)
    gets it live if one happens to be listening, but nothing here ever
    waits for or requires that. Ticks/alerts are already durably written
    to Postgres by the time this is called, so a Redis outage costs only
    the live-push feature, never data.
    """
    if time.time() < _publish_state["cooldown_until"]:
        # Already known-down -- skip the network call entirely rather
        # than pay socket_connect_timeout again for a Redis we just
        # failed to reach a moment ago.
        return

    try:
        redis_client.publish(channel, json.dumps(payload, default=str))
        _publish_state["failures"] = 0
    except redis.RedisError as e:
        _publish_state["failures"] += 1
        if _publish_state["failures"] >= PUBLISH_FAILURE_THRESHOLD:
            _publish_state["cooldown_until"] = time.time() + PUBLISH_COOLDOWN_SECONDS
        print(f"Redis publish to '{channel}' failed (non-fatal): {e}")


def wait_for_schema(max_retries=30, retry_delay=5):
    """
    Reflect the symbols/ticks/alerts tables, retrying until they exist.

    This service can start before Alembic has created the schema: on a
    completely fresh cluster, every Deployment (including this one) gets
    applied at once, and the migration only runs afterward, as a
    separate script step. Never showed up on Kind during this project's
    iteration (its Postgres already had the schema from earlier runs),
    but is a real race on a first-ever deploy -- exactly what AKS
    validation exists to catch. Don't assume dependency ordering; wait
    for it instead.
    """
    for attempt in range(1, max_retries + 1):
        try:
            metadata = MetaData()
            metadata.reflect(bind=engine, only=["symbols", "ticks", "alerts"])
            return (
                metadata.tables["symbols"],
                metadata.tables["ticks"],
                metadata.tables["alerts"],
            )
        except Exception as e:
            print(f"[{attempt}/{max_retries}] Schema not ready yet ({e}) -- retrying in {retry_delay}s...")
            time.sleep(retry_delay)

    raise RuntimeError(
        f"Gave up after {max_retries} attempts -- symbols/ticks/alerts tables never appeared."
    )


symbols_table, ticks_table, alerts_table = wait_for_schema()


def load_symbol_map(max_retries=30, retry_delay=5):
    """ticker -> symbol_id, for every active symbol. Retries until seeded."""
    for attempt in range(1, max_retries + 1):
        with engine.connect() as conn:
            rows = conn.execute(
                select(symbols_table.c.id, symbols_table.c.ticker)
                .where(symbols_table.c.is_active.is_(True))
            )
            symbol_map = {row.ticker: row.id for row in rows}

        if symbol_map:
            return symbol_map

        print(f"[{attempt}/{max_retries}] symbols table is empty -- waiting for seed data...")
        time.sleep(retry_delay)

    raise RuntimeError(
        f"Gave up after {max_retries} attempts -- no active symbols found. "
        "Has the database been seeded?"
    )


SYMBOL_MAP = load_symbol_map()

print(f"Loaded {len(SYMBOL_MAP)} active symbols: {list(SYMBOL_MAP)}")


def insert_tick(symbol_id, price, volume, traded_at):
    with engine.begin() as conn:
        conn.execute(
            ticks_table.insert().values(
                symbol_id=symbol_id,
                price=price,
                volume=volume,
                traded_at=traded_at,
            )
        )


def insert_alert(symbol_id, message, severity):
    # created_at has a server_default (see app/database/models.py), so it's
    # not set here -- same pattern as insert_tick leaving created_at to the
    # database.
    with engine.begin() as conn:
        conn.execute(
            alerts_table.insert().values(
                symbol_id=symbol_id,
                message=message,
                severity=severity,
            )
        )


def on_message(ws, message):
    payload = json.loads(message)

    if payload.get("type") != "trade":
        return

    for trade in payload.get("data", []):
        ticker = trade["s"]
        symbol_id = SYMBOL_MAP.get(ticker)

        if symbol_id is None:
            # Trade for a symbol we're not tracking -- shouldn't happen
            # since we only subscribe to what's in SYMBOL_MAP, but skip
            # defensively rather than crash the whole service on it.
            continue

        traded_at = datetime.fromtimestamp(
            trade["t"] / 1000, tz=timezone.utc
        )

        insert_tick(
            symbol_id=symbol_id,
            price=trade["p"],
            volume=trade["v"],
            traded_at=traded_at,
        )

        TICKS_INGESTED_TOTAL.inc()

        print(f"{ticker}: {trade['p']} x {trade['v']} @ {traded_at}")

        publish_event("ticks", {
            "type": "tick",
            "symbol_id": symbol_id,
            "ticker": ticker,
            "price": trade["p"],
            "volume": trade["v"],
            "traded_at": traded_at.isoformat(),
        })

        for severity, message in detector.check_tick(
            ticker, trade["p"], trade["v"], traded_at
        ):
            insert_alert(symbol_id, message, severity)
            ALERTS_TOTAL.labels(severity=severity).inc()
            print(f"  [{severity}] {ticker}: {message}")

            publish_event("alerts", {
                "type": "alert",
                "symbol_id": symbol_id,
                "ticker": ticker,
                "message": message,
                "severity": severity,
            })


# Set by on_error, read by run() after ws.run_forever() returns -- lets
# the reconnect logic tell a 429 (Finnhub's own connection-rate limit)
# apart from an ordinary dropped connection, without changing
# websocket-client's on_error/on_close callback signatures to smuggle it
# through some other way.
_last_error = {"value": None}

BASE_RECONNECT_DELAY = 5
MAX_RECONNECT_DELAY = 60


def on_error(ws, error):
    _last_error["value"] = error
    print("WebSocket error:", error)


def on_close(ws, close_status_code, close_msg):
    print("WebSocket closed:", close_status_code, close_msg)


def on_open(ws):
    for ticker in SYMBOL_MAP:
        ws.send(json.dumps({"type": "subscribe", "symbol": ticker}))
    print(f"Subscribed to: {list(SYMBOL_MAP)}")


def _rate_limit_wait_seconds(error):
    """
    If `error` is a 429 handshake rejection carrying Finnhub's own
    x-ratelimit-reset header, how long to wait until that reset (plus a
    small buffer) -- None otherwise.

    Retrying a 429 on the same flat delay as an ordinary dropped
    connection is actively self-defeating: Finnhub's free tier only
    allows a handful of new connection attempts per short window
    (observed live: x-ratelimit-limit: 5), so hammering it every 5s
    burns through that budget in seconds and then keeps getting
    rejected for the rest of the window -- seen live as a real,
    sustained reconnect storm with almost no actual connected time,
    starving every symbol's tick flow, not just one.
    """
    if not isinstance(error, websocket.WebSocketBadStatusException):
        return None
    if error.status_code != 429:
        return None

    reset_at = (error.resp_headers or {}).get("x-ratelimit-reset")
    if reset_at is None:
        return None

    try:
        return max(float(reset_at) - time.time(), 0) + 2
    except (TypeError, ValueError):
        return None


def run():
    start_http_server(8001)
    print("Metrics server listening on :8001/metrics")

    backoff = BASE_RECONNECT_DELAY

    while True:
        _last_error["value"] = None
        connected_at = time.time()

        ws = websocket.WebSocketApp(
            f"wss://ws.finnhub.io?token={FINNHUB_API_KEY}",
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )
        # Blocks until the connection drops (error, server close, network
        # blip); when it returns, reconnect rather than let the process
        # exit and crash-loop.
        ws.run_forever()

        # Stayed up a while -- the backoff already did its job. Reset it
        # so one future blip doesn't inherit a wait time built up from
        # much earlier trouble.
        if time.time() - connected_at > MAX_RECONNECT_DELAY:
            backoff = BASE_RECONNECT_DELAY

        rate_limit_wait = _rate_limit_wait_seconds(_last_error["value"])
        if rate_limit_wait is not None:
            delay = rate_limit_wait
        else:
            delay = backoff
            backoff = min(backoff * 2, MAX_RECONNECT_DELAY)

        print(f"Connection lost -- reconnecting in {delay:.0f} seconds...")
        time.sleep(delay)


if __name__ == "__main__":
    run()

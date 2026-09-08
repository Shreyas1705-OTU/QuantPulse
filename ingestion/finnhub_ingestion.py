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

MUST run as a single replica -- see k8s/ingestion/deployment.yaml.
"""

import json
import os
import time
from datetime import datetime, timezone

import websocket
from prometheus_client import Counter, start_http_server
from sqlalchemy import create_engine, MetaData, select

from anomaly_detector import AnomalyDetector

DATABASE_URL = os.environ["DATABASE_URL"]
FINNHUB_API_KEY = os.environ["FINNHUB_API_KEY"]

TICKS_INGESTED_TOTAL = Counter(
    "quantpulse_ticks_ingested_total",
    "Total market ticks ingested from Finnhub",
)

# Moved here from backend/app/core/metrics.py -- the backend has no code
# path that ever creates an Alert (no POST /alerts route), so that counter
# could never fire. Real alerts are only ever created here, by the
# anomaly detector, so this is the real place for the metric.
ALERTS_TOTAL = Counter(
    "quantpulse_alerts_total",
    "Total alerts generated",
)

engine = create_engine(DATABASE_URL)
detector = AnomalyDetector()


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

        for severity, message in detector.check_tick(
            ticker, trade["p"], trade["v"], traded_at
        ):
            insert_alert(symbol_id, message, severity)
            ALERTS_TOTAL.inc()
            print(f"  [{severity}] {ticker}: {message}")


def on_error(ws, error):
    print("WebSocket error:", error)


def on_close(ws, close_status_code, close_msg):
    print("WebSocket closed:", close_status_code, close_msg)


def on_open(ws):
    for ticker in SYMBOL_MAP:
        ws.send(json.dumps({"type": "subscribe", "symbol": ticker}))
    print(f"Subscribed to: {list(SYMBOL_MAP)}")


def run():
    start_http_server(8001)
    print("Metrics server listening on :8001/metrics")

    while True:
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
        print("Connection lost -- reconnecting in 5 seconds...")
        time.sleep(5)


if __name__ == "__main__":
    run()

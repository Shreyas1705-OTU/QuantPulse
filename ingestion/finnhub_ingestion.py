"""
QuantPulse Finnhub ingestion service.

Connects to Finnhub's WebSocket, subscribes to every active symbol in
the `symbols` table, and writes each trade as a row in `ticks`. Runs as
a long-lived worker process -- separate from the FastAPI backend, its
own Dockerfile/deployment (see k8s/ingestion/). Writes directly to
Postgres via SQLAlchemy Core (reflecting the existing tables rather than
duplicating column definitions), not through the backend's API.

Exposes its own /metrics endpoint on :8001 -- this is the real place
"ticks ingested" belongs, since the backend never touches these writes.

MUST run as a single replica -- see k8s/ingestion/deployment.yaml.
"""

import json
import os
import time
from datetime import datetime, timezone

import websocket
from prometheus_client import Counter, start_http_server
from sqlalchemy import create_engine, MetaData, select

DATABASE_URL = os.environ["DATABASE_URL"]
FINNHUB_API_KEY = os.environ["FINNHUB_API_KEY"]

TICKS_INGESTED_TOTAL = Counter(
    "quantpulse_ticks_ingested_total",
    "Total market ticks ingested from Finnhub",
)

engine = create_engine(DATABASE_URL)
metadata = MetaData()
metadata.reflect(bind=engine, only=["symbols", "ticks"])

symbols_table = metadata.tables["symbols"]
ticks_table = metadata.tables["ticks"]


def load_symbol_map():
    """ticker -> symbol_id, for every active symbol."""
    with engine.connect() as conn:
        rows = conn.execute(
            select(symbols_table.c.id, symbols_table.c.ticker)
            .where(symbols_table.c.is_active.is_(True))
        )
        return {row.ticker: row.id for row in rows}


SYMBOL_MAP = load_symbol_map()

if not SYMBOL_MAP:
    raise RuntimeError(
        "No active symbols found -- has the database been seeded?"
    )

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

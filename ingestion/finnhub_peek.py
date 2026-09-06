"""
Throwaway script: connect to Finnhub's WebSocket and print raw trade
messages, to see the actual data shape before designing the Symbol/Tick
model around it. Not part of the app -- exploration only.

Reads the API key from the FINNHUB_API_KEY env var (never hardcode it
in a file that might get committed).
"""

import json
import os
import websocket

API_KEY = os.environ["FINNHUB_API_KEY"]

# One US equity (only trades during NYSE hours) + one forex pair
# (trades ~24/5) -- so we see live data regardless of what time it is.
SYMBOLS = ["AAPL", "OANDA:EUR_USD"]


def on_message(ws, message):
    data = json.loads(message)
    print(json.dumps(data, indent=2))


def on_error(ws, error):
    print("ERROR:", error)


def on_close(ws, close_status_code, close_msg):
    print("### connection closed ###")


def on_open(ws):
    for symbol in SYMBOLS:
        ws.send(json.dumps({"type": "subscribe", "symbol": symbol}))
    print(f"Subscribed to: {SYMBOLS}")


if __name__ == "__main__":
    ws = websocket.WebSocketApp(
        f"wss://ws.finnhub.io?token={API_KEY}",
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
    )
    ws.run_forever()

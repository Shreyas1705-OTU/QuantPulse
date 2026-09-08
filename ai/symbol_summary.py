"""
QuantPulse per-symbol running summary.

Recurring job (k8s CronJob every 15 minutes, see
k8s/ai/symbol-summary-cronjob.yaml): for every active symbol, asks Azure
OpenAI for a short "how's the session going" read of that symbol's recent
trading, caches it in symbol_summaries (one row per symbol, upserted).

Distinct from ai/daily_summary.py, which writes one shared digest once a
day from that day's alerts only -- this is a continuous, per-symbol
narrative that keeps refreshing throughout market hours. That's the
whole point of it: visible proof the AI layer is doing something all the
time the system runs, not just once at close.

Skips a symbol entirely (no LLM call, no write) if no new ticks have
landed since its last summary -- an idle or closed symbol shouldn't cost
anything just because the CronJob fired on schedule.
"""

import sys

from sqlalchemy import select, func, insert, update

from db import engine, reflect_tables
from llm_client import build_client, summarize_symbol_day

# Same window Price Trends/Current Trade Summary use on the dashboard --
# the AI's "session so far" read should describe the same slice of data
# the user is looking at, not some other lookback.
TICK_WINDOW = 30


def run():
    tables = reflect_tables(["symbols", "ticks", "alerts", "symbol_summaries"])
    symbols_table = tables["symbols"]
    ticks_table = tables["ticks"]
    alerts_table = tables["alerts"]
    summaries_table = tables["symbol_summaries"]

    with engine.connect() as conn:
        symbols = conn.execute(
            select(
                symbols_table.c.id,
                symbols_table.c.ticker,
                symbols_table.c.display_name,
                symbols_table.c.asset_type,
            ).where(symbols_table.c.is_active.is_(True))
        ).fetchall()

        existing = {
            row.symbol_id: row
            for row in conn.execute(select(summaries_table)).fetchall()
        }

    if not symbols:
        print("No active symbols -- nothing to do.")
        return

    client = None  # built lazily -- never touched if every symbol is skipped
    updated = 0
    skipped = 0

    for sym in symbols:
        with engine.connect() as conn:
            latest_tick = conn.execute(
                select(ticks_table.c.id)
                .where(ticks_table.c.symbol_id == sym.id)
                .order_by(ticks_table.c.id.desc())
                .limit(1)
            ).first()

        if latest_tick is None:
            print(f"{sym.ticker}: no ticks yet -- skipping")
            skipped += 1
            continue

        prior = existing.get(sym.id)
        if prior and prior.through_tick_id == latest_tick.id:
            print(f"{sym.ticker}: no new ticks since last summary -- skipping")
            skipped += 1
            continue

        with engine.connect() as conn:
            ticks = conn.execute(
                select(ticks_table.c.price)
                .where(ticks_table.c.symbol_id == sym.id)
                .order_by(ticks_table.c.id.desc())
                .limit(TICK_WINDOW)
            ).fetchall()

            alert_count = conn.execute(
                select(func.count())
                .select_from(alerts_table)
                .where(alerts_table.c.symbol_id == sym.id)
            ).scalar()

        # Newest-first from the query above -- prices[0] is the latest
        # trade, prices[-1] is the oldest one still in this window. Using
        # that as "start of window" rather than a real session-open price
        # mirrors the same tradeoff the frontend's own change% already
        # makes (see PriceTrendCard's computeChange) -- there's no
        # persisted real market-open price to compare against yet.
        prices = [t.price for t in ticks]

        if client is None:
            client = build_client()

        try:
            summary_text = summarize_symbol_day(
                client,
                ticker=sym.ticker,
                display_name=sym.display_name,
                asset_type=sym.asset_type,
                window_open=prices[-1],
                latest_price=prices[0],
                high=max(prices),
                low=min(prices),
                alert_count=alert_count,
            )

            with engine.begin() as conn:
                if prior:
                    conn.execute(
                        update(summaries_table)
                        .where(summaries_table.c.symbol_id == sym.id)
                        .values(
                            summary_text=summary_text,
                            through_tick_id=latest_tick.id,
                        )
                    )
                else:
                    conn.execute(
                        insert(summaries_table).values(
                            symbol_id=sym.id,
                            summary_text=summary_text,
                            through_tick_id=latest_tick.id,
                        )
                    )

        except Exception as e:
            # One bad LLM call or write must not sink the rest of the
            # batch -- this symbol just keeps its last-known summary
            # (or none) and gets picked up again next run.
            print(f"  {sym.ticker}: FAILED ({e}) -- will retry next run")
            continue

        updated += 1
        print(f"  {sym.ticker}: {summary_text}")

    print(f"Updated {updated}/{len(symbols)} symbol summaries ({skipped} skipped, no new data).")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        print(f"FATAL: {e}")
        sys.exit(1)

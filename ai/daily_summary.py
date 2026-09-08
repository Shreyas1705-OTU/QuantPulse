"""
QuantPulse end-of-day summary.

One-shot job (run as a k8s CronJob once a day, see
k8s/ai/daily-summary-cronjob.yaml): gathers the day's alerts, asks Azure
OpenAI for a short digest, caches it in daily_summaries. Idempotent -- if
a row for today already exists, this is a no-op, so a re-triggered or
manually-run job can't double-write or double-spend.

Skips the LLM call entirely on a quiet day (no alerts) -- a canned
"all quiet" message costs nothing and says the same thing a generated
one would.
"""

import sys
from datetime import datetime, timezone

from sqlalchemy import select

from db import engine, reflect_tables
from llm_client import build_client, summarize_day


def run():
    tables = reflect_tables(["alerts", "symbols", "daily_summaries"])
    alerts_table = tables["alerts"]
    symbols_table = tables["symbols"]
    summaries_table = tables["daily_summaries"]

    today = datetime.now(timezone.utc).date()

    with engine.connect() as conn:
        existing = conn.execute(
            select(summaries_table.c.id)
            .where(summaries_table.c.summary_date == today)
        ).first()

    if existing:
        print(f"Summary for {today} already exists -- nothing to do.")
        return

    day_start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)

    with engine.connect() as conn:
        rows = conn.execute(
            select(
                alerts_table.c.severity,
                alerts_table.c.message,
                symbols_table.c.ticker,
            )
            .select_from(
                alerts_table.join(
                    symbols_table,
                    alerts_table.c.symbol_id == symbols_table.c.id,
                )
            )
            .where(alerts_table.c.created_at >= day_start)
            .order_by(alerts_table.c.created_at)
        ).fetchall()

    if not rows:
        summary_text = "No notable anomalies detected today across any tracked symbol."
    else:
        client = build_client()
        alert_summaries = [
            {"ticker": r.ticker, "severity": r.severity, "message": r.message}
            for r in rows
        ]
        summary_text = summarize_day(client, today.isoformat(), alert_summaries)

    # summary_date has a unique index -- if two invocations somehow race
    # past the "already exists" check above, the second insert fails
    # loudly instead of creating a duplicate row.
    with engine.begin() as conn:
        conn.execute(
            summaries_table.insert().values(
                summary_date=today,
                summary_text=summary_text,
            )
        )

    print(f"Summary for {today} written ({len(rows)} alert(s) considered).")
    print(summary_text)


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        print(f"FATAL: {e}")
        sys.exit(1)

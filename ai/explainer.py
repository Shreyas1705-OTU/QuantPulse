"""
QuantPulse alert explainer.

One-shot job (run as a k8s CronJob every couple of minutes, see
k8s/ai/explainer-cronjob.yaml): finds Alert rows with no explanation yet,
asks Azure OpenAI for a short plain-English explanation of each, writes
it back. Bounded per run (BATCH_LIMIT) so a backlog can't turn one
invocation into unbounded API spend/time -- whatever's left over is
picked up by the next scheduled run.

Deliberately decoupled from ingestion/anomaly_detector.py: the alert
itself is created instantly there, with no dependency on this job ever
running successfully. A failed or slow Azure OpenAI call here can never
block real-time tick ingestion.
"""

import sys

from sqlalchemy import select, update

from db import engine, reflect_tables
from llm_client import build_client, explain_alert

BATCH_LIMIT = 20


def run():
    tables = reflect_tables(["alerts", "symbols"])
    alerts_table = tables["alerts"]
    symbols_table = tables["symbols"]

    with engine.connect() as conn:
        rows = conn.execute(
            select(
                alerts_table.c.id,
                alerts_table.c.severity,
                alerts_table.c.message,
                symbols_table.c.ticker,
                symbols_table.c.display_name,
                symbols_table.c.asset_type,
            )
            .select_from(
                alerts_table.join(
                    symbols_table,
                    alerts_table.c.symbol_id == symbols_table.c.id,
                )
            )
            .where(alerts_table.c.explanation.is_(None))
            .order_by(alerts_table.c.id)
            .limit(BATCH_LIMIT)
        ).fetchall()

    if not rows:
        print("No unexplained alerts -- nothing to do.")
        return

    print(f"Explaining {len(rows)} alert(s)...")

    client = build_client()
    explained = 0

    for row in rows:
        try:
            explanation = explain_alert(
                client,
                ticker=row.ticker,
                display_name=row.display_name,
                asset_type=row.asset_type,
                severity=row.severity,
                message=row.message,
            )

            # Write-back shares the try with the LLM call, not a separate
            # one after it -- if the LLM succeeds but this UPDATE hits a
            # transient DB hiccup (a dropped connection, a lock timeout),
            # that must not propagate uncaught and kill the whole job
            # (and the rest of the batch with it). The row stays NULL
            # either way, so next run just costs one extra LLM call, never
            # data corruption -- this is exactly the same "one bad thing
            # can't sink the batch" guarantee the LLM call already had.
            with engine.begin() as conn:
                conn.execute(
                    update(alerts_table)
                    .where(alerts_table.c.id == row.id)
                    .values(explanation=explanation)
                )

        except Exception as e:
            # One bad call or write (rate limit, transient network error,
            # a dropped DB connection) must not sink the rest of the
            # batch -- leave it NULL, next run retries.
            print(f"  alert {row.id}: FAILED ({e}) -- will retry next run")
            continue

        explained += 1
        print(f"  alert {row.id} ({row.ticker}): {explanation}")

    print(f"Explained {explained}/{len(rows)} alert(s).")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        print(f"FATAL: {e}")
        sys.exit(1)

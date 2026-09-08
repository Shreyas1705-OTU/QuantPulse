"""
Shared DB engine + table reflection for the ai/ worker scripts.

explainer.py, daily_summary.py, and symbol_summary.py are all one-shot
CronJob invocations, not long-lived processes (see k8s/ai/) -- unlike
ingestion's wait_for_schema (30 retries over ~2.5 minutes, since a
Deployment pod that gives up just sits crashed until someone notices),
a short retry here is enough: if the schema genuinely isn't ready, the
job exits non-zero and the *next scheduled run* tries again on its own.

max_retries=10/retry_delay=3 (30s total) rather than the original 5/3
(15s): observed live on a freshly-started AKS cluster that 15s wasn't
quite enough to outlast a cold-start DNS race ("postgres" not yet
resolving), producing a harmless but noisy Error pod that only
self-healed on the *next* scheduled trigger. explainer.py runs every 2
minutes, so that cost was small either way -- but symbol_summary.py
runs only every 15 minutes, where the same miss means a much longer
wait before it tries again. Doubling the budget here trades a little
extra worst-case job runtime (still bounded, still short) for
meaningfully fewer of these cold-start misses across all three
callers.
"""

import os
import time

from sqlalchemy import create_engine, MetaData

DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_engine(DATABASE_URL)


def reflect_tables(table_names, max_retries=10, retry_delay=3):
    for attempt in range(1, max_retries + 1):
        try:
            metadata = MetaData()
            metadata.reflect(bind=engine, only=table_names)
            return {name: metadata.tables[name] for name in table_names}
        except Exception as e:
            print(f"[{attempt}/{max_retries}] Schema not ready yet ({e}) -- retrying in {retry_delay}s...")
            time.sleep(retry_delay)

    raise RuntimeError(
        f"Gave up after {max_retries} attempts -- {table_names} never appeared."
    )

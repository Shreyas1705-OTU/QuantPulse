"""
Shared fixtures for the ai/ test suite. These tests run against a REAL
Postgres (not sqlite, not mocks) -- the same discipline used throughout
this project's manual testing, since ai/db.py's reflect_tables and the
raw SQL in explainer.py/symbol_summary.py depend on real Postgres
behavior. Point TEST_DATABASE_URL at a throwaway database with the
schema already migrated (see README's testing section); defaults to the
local port used by the project's own dev Postgres container.

DATABASE_URL must be set in os.environ BEFORE ai/db.py (or explainer.py/
symbol_summary.py, which import it) is ever imported -- db.py reads it
at module import time. Setting it here, at conftest collection time,
guarantees that ordering: pytest always loads a directory's conftest.py
before importing any test module in that directory.
"""

import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://quantpulse:quantpulse123@localhost:5433/quantpulse",
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Symbols are treated as fixed reference data for this whole test session
# (cheap to share, nothing here mutates them) -- only the tables these
# scripts actually write to get reset around each test.
_SEED_SYMBOLS = [
    ("AAPL", "Apple Inc.", "equity"),
    ("TSLA", "Tesla, Inc.", "equity"),
    ("MSFT", "Microsoft Corporation", "equity"),
]


@pytest.fixture(scope="session", autouse=True)
def _seed_symbols_once():
    engine = create_engine(TEST_DATABASE_URL)
    with engine.begin() as conn:
        existing = {
            row.ticker
            for row in conn.execute(text("SELECT ticker FROM symbols"))
        }
        for ticker, display_name, asset_type in _SEED_SYMBOLS:
            if ticker not in existing:
                conn.execute(
                    text(
                        "INSERT INTO symbols (ticker, display_name, asset_type, is_active) "
                        "VALUES (:t, :d, :a, true)"
                    ),
                    {"t": ticker, "d": display_name, "a": asset_type},
                )
    engine.dispose()


@pytest.fixture(autouse=True)
def clean_tables():
    """Every ai/ test starts and ends with alerts/symbol_summaries/ticks
    empty -- keeps each test's DB state fully isolated from every other,
    regardless of run order."""
    engine = create_engine(TEST_DATABASE_URL)

    def _wipe():
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM symbol_summaries"))
            conn.execute(text("DELETE FROM alerts"))
            conn.execute(text("DELETE FROM ticks"))

    _wipe()
    yield
    _wipe()
    engine.dispose()


@pytest.fixture
def symbol_ids():
    engine = create_engine(TEST_DATABASE_URL)
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT id, ticker FROM symbols")).fetchall()
    engine.dispose()
    return {r.ticker: r.id for r in rows}

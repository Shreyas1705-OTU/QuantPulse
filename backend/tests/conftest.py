"""
Shared fixtures for the backend service-layer tests. Real Postgres, not
sqlite -- TickService.get_latest_tick_per_symbol uses Postgres's
DISTINCT ON, which sqlite doesn't have and wouldn't meaningfully test
anyway.

DATABASE_URL must be set before app.database.connection (or anything
importing it) is ever imported -- app/core/config.py's Settings reads it
at class-definition time. Setting it here, at conftest collection time,
guarantees that ordering the same way ai/tests/conftest.py does.
"""

import logging
import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import text

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://quantpulse:quantpulse123@localhost:5433/quantpulse",
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

# app/database/connection.py hardcodes echo=True on its engine -- fine
# for a running server, but floods test output with every statement.
# Suppressing the logger it echoes through, not the app code itself.
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database.connection import SessionLocal  # noqa: E402

_SEED_SYMBOLS = [
    ("AAPL", "Apple Inc.", "equity"),
    ("TSLA", "Tesla, Inc.", "equity"),
    ("MSFT", "Microsoft Corporation", "equity"),
]


@pytest.fixture(scope="session", autouse=True)
def _seed_symbols_once():
    db = SessionLocal()
    try:
        existing = {row[0] for row in db.execute(text("SELECT ticker FROM symbols"))}
        for ticker, display_name, asset_type in _SEED_SYMBOLS:
            if ticker not in existing:
                db.execute(
                    text(
                        "INSERT INTO symbols (ticker, display_name, asset_type, is_active) "
                        "VALUES (:t, :d, :a, true)"
                    ),
                    {"t": ticker, "d": display_name, "a": asset_type},
                )
        db.commit()
    finally:
        db.close()


@pytest.fixture(autouse=True)
def clean_tables():
    """Every service test starts and ends with ticks/alerts/summaries
    empty and users cleared -- symbols stay seeded and untouched."""
    db = SessionLocal()

    def _wipe():
        db.execute(text("DELETE FROM symbol_summaries"))
        db.execute(text("DELETE FROM alerts"))
        db.execute(text("DELETE FROM ticks"))
        db.execute(text("DELETE FROM daily_summaries"))
        db.execute(text("DELETE FROM users"))
        db.commit()

    _wipe()
    yield db
    _wipe()
    db.close()


@pytest.fixture
def db_session(clean_tables):
    return clean_tables


@pytest.fixture
def symbol_ids(db_session):
    rows = db_session.execute(text("SELECT id, ticker FROM symbols")).fetchall()
    return {r.ticker: r.id for r in rows}

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    ForeignKey,
    DateTime,
    Date,
    Text,
)
from sqlalchemy.sql import func

from app.database.base import Base


class Symbol(Base):
    __tablename__ = "symbols"

    id = Column(Integer, primary_key=True, index=True)

    ticker = Column(String(50), unique=True, nullable=False, index=True)
    display_name = Column(String(100), nullable=False)

    # "equity" | "forex" | "crypto" -- drives market-hours logic later
    # (equities: NYSE hours only, forex: ~24/5, crypto: 24/7)
    asset_type = Column(String(20), nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    username = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )

    email = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True
    )

    hashed_password = Column(
        String(255),
        nullable=False
    )

    role = Column(
        String(20),
        default="user",
        nullable=False
    )


class Tick(Base):
    __tablename__ = "ticks"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    symbol_id = Column(
        Integer,
        ForeignKey("symbols.id"),
        nullable=False,
        index=True
    )

    price = Column(
        Float,
        nullable=False
    )

    volume = Column(
        Float,
        nullable=False
    )

    # When the trade actually executed (Finnhub's `t`), distinct from
    # created_at -- our own ingestion time can lag this slightly.
    traded_at = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    symbol_id = Column(
        Integer,
        ForeignKey("symbols.id"),
        nullable=False
    )

    message = Column(
        String(255),
        nullable=False
    )

    severity = Column(
        String(20),
        nullable=False
    )

    # Filled in shortly after creation by the ai/explainer.py worker
    # (Azure OpenAI), not at insert time -- the anomaly detector that
    # creates this row must never block on an external API call. NULL
    # means "not explained yet", not an error.
    explanation = Column(
        Text,
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )


class DailySummary(Base):
    __tablename__ = "daily_summaries"

    id = Column(Integer, primary_key=True, index=True)

    # One row per calendar day (UTC) -- written once by
    # ai/daily_summary.py, cached and served as-is rather than
    # recomputed per request.
    summary_date = Column(Date, unique=True, nullable=False, index=True)

    summary_text = Column(Text, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

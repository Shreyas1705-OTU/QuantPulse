from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.models import Tick


class TickService:

    def __init__(self, db: Session):
        self.db = db

    def create_tick(
        self,
        symbol_id: int,
        price: float,
        volume: float,
        traded_at,
    ):
        tick = Tick(
            symbol_id=symbol_id,
            price=price,
            volume=volume,
            traded_at=traded_at,
        )

        self.db.add(tick)
        self.db.commit()
        self.db.refresh(tick)

        # Anomaly detection (z-score/Bollinger on price/volume) and the
        # resulting alerts are Phase 3 work -- intentionally not here yet.

        return tick

    def get_all_ticks(self, limit: int = 50):
        # Ingestion writes real ticks continuously (crypto trades 24/7),
        # so this table only grows -- always cap, never return the whole
        # thing. Use count_ticks() for a total instead of len(get_all_ticks()).
        return (
            self.db.query(Tick)
            .order_by(Tick.traded_at.desc())
            .limit(limit)
            .all()
        )

    def count_ticks(self) -> int:
        return self.db.query(func.count(Tick.id)).scalar()

    def get_ticks_for_symbol(
        self,
        symbol_id: int,
        limit: int = 200,
    ):
        return (
            self.db.query(Tick)
            .filter(Tick.symbol_id == symbol_id)
            .order_by(Tick.traded_at.desc())
            .limit(limit)
            .all()
        )

    def get_latest_tick_per_symbol(self):
        # One row per symbol_id (its most recent tick) -- this is what
        # lets the dashboard show a last-known price for a symbol whose
        # market is currently closed, instead of nothing. Postgres's
        # DISTINCT ON requires the ORDER BY to start with the same
        # column(s) passed to .distinct(), which this does. id.desc() is
        # just a deterministic tiebreaker for the (unlikely, but not
        # impossible) case of two ticks sharing the same traded_at.
        return (
            self.db.query(Tick)
            .distinct(Tick.symbol_id)
            .order_by(Tick.symbol_id, Tick.traded_at.desc(), Tick.id.desc())
            .all()
        )

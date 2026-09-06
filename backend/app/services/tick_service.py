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

    def get_all_ticks(self):
        return (
            self.db.query(Tick)
            .order_by(Tick.traded_at.desc())
            .all()
        )

    def get_ticks_for_symbol(
        self,
        symbol_id: int,
    ):
        return (
            self.db.query(Tick)
            .filter(Tick.symbol_id == symbol_id)
            .order_by(Tick.traded_at.desc())
            .all()
        )

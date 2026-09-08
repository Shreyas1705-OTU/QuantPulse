from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.metrics import ALERTS_TOTAL
from app.database.models import Alert


class AlertService:

    def __init__(self, db: Session):
        self.db = db

    def create_alert(
        self,
        symbol_id: int,
        message: str,
        severity: str,
    ):
        alert = Alert(
            symbol_id=symbol_id,
            message=message,
            severity=severity,
        )

        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)

        ALERTS_TOTAL.inc()

        return alert

    def get_all_alerts(self, limit: int = 50):
        # Phase 3 will start writing real alerts continuously -- cap this
        # the same way as TickService.get_all_ticks(). Use count_alerts()
        # for a total instead of len(get_all_alerts()).
        return (
            self.db.query(Alert)
            .order_by(Alert.created_at.desc())
            .limit(limit)
            .all()
        )

    def count_alerts(self) -> int:
        return self.db.query(func.count(Alert.id)).scalar()

    def get_alerts_for_symbol(
        self,
        symbol_id: int,
        limit: int = 100,
    ):
        return (
            self.db.query(Alert)
            .filter(Alert.symbol_id == symbol_id)
            .order_by(Alert.created_at.desc())
            .limit(limit)
            .all()
        )

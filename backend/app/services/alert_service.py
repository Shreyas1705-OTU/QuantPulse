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

    def get_all_alerts(self):
        return (
            self.db.query(Alert)
            .order_by(Alert.created_at.desc())
            .all()
        )

    def get_alerts_for_symbol(
        self,
        symbol_id: int,
    ):
        return (
            self.db.query(Alert)
            .filter(Alert.symbol_id == symbol_id)
            .order_by(Alert.created_at.desc())
            .all()
        )

from datetime import date

from sqlalchemy.orm import Session

from app.database.models import DailySummary


class SummaryService:

    def __init__(self, db: Session):
        self.db = db

    def get_summary_for_date(self, summary_date: date):
        return (
            self.db.query(DailySummary)
            .filter(DailySummary.summary_date == summary_date)
            .first()
        )

    def get_latest_summary(self):
        # Falls back to the most recent cached summary when today's hasn't
        # been generated yet (e.g. before the daily CronJob has run) --
        # ai/daily_summary.py is the only writer.
        return (
            self.db.query(DailySummary)
            .order_by(DailySummary.summary_date.desc())
            .first()
        )

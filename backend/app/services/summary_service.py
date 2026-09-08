from datetime import date

from sqlalchemy.orm import Session

from app.database.models import DailySummary, Symbol, SymbolSummary


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

    def get_symbol_summaries(self):
        # One row per symbol that has one yet -- a symbol with no ticks,
        # or whose first ai/symbol_summary.py run hasn't fired since it
        # started trading, just doesn't appear (not an error, nothing to
        # 404 on -- the caller renders an empty list as "no summary yet"
        # per symbol).
        return (
            self.db.query(
                SymbolSummary.symbol_id,
                Symbol.ticker,
                SymbolSummary.summary_text,
                SymbolSummary.updated_at,
            )
            .join(Symbol, Symbol.id == SymbolSummary.symbol_id)
            .order_by(Symbol.ticker)
            .all()
        )

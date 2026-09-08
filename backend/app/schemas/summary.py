from datetime import date, datetime

from pydantic import BaseModel


class DailySummaryResponse(BaseModel):
    summary_date: date
    summary_text: str
    created_at: datetime

    class Config:
        from_attributes = True


class SymbolSummaryResponse(BaseModel):
    symbol_id: int
    ticker: str
    summary_text: str
    updated_at: datetime

    class Config:
        from_attributes = True

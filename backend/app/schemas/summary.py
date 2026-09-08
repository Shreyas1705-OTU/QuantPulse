from datetime import date, datetime

from pydantic import BaseModel


class DailySummaryResponse(BaseModel):
    summary_date: date
    summary_text: str
    created_at: datetime

    class Config:
        from_attributes = True

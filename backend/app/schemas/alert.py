from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AlertCreate(BaseModel):
    symbol_id: int
    message: str
    severity: str


class AlertResponse(BaseModel):
    id: int
    symbol_id: int
    message: str
    severity: str
    # None until ai/explainer.py fills it in -- expected to lag the alert
    # itself by up to one explainer cycle, not a bug.
    explanation: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

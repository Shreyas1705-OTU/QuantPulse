from datetime import datetime

from pydantic import BaseModel


class TickCreate(BaseModel):
    symbol_id: int
    price: float
    volume: float
    traded_at: datetime


class TickResponse(BaseModel):
    id: int
    symbol_id: int
    price: float
    volume: float
    traded_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True

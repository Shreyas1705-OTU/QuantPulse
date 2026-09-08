from pydantic import BaseModel, ConfigDict, computed_field

from app.core.market_hours import is_market_open


class SymbolCreate(BaseModel):
    ticker: str
    display_name: str
    asset_type: str
    is_active: bool = True


class SymbolResponse(BaseModel):
    id: int
    ticker: str
    display_name: str
    asset_type: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)

    # Computed at serialization time from asset_type + the real current
    # time -- never stored, always accurate to "right now" rather than
    # whenever this row was last written.
    @computed_field
    @property
    def is_market_open(self) -> bool:
        return is_market_open(self.asset_type)

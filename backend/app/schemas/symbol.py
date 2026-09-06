from pydantic import BaseModel, ConfigDict


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

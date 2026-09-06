from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database.session import get_db
from app.schemas.symbol import SymbolCreate, SymbolResponse
from app.services.symbol_service import SymbolService

router = APIRouter(
    prefix="/symbols",
    tags=["Symbols"],
)


@router.get("/", response_model=list[SymbolResponse])
def get_symbols(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = SymbolService(db)
    return service.get_all_symbols()


@router.get("/{symbol_id}", response_model=SymbolResponse)
def get_symbol(
    symbol_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = SymbolService(db)

    symbol = service.get_symbol(symbol_id)

    if not symbol:
        raise HTTPException(
            status_code=404,
            detail="Symbol not found",
        )

    return symbol


@router.post("/", response_model=SymbolResponse, status_code=201)
def create_symbol(
    symbol: SymbolCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = SymbolService(db)

    return service.create_symbol(
        ticker=symbol.ticker,
        display_name=symbol.display_name,
        asset_type=symbol.asset_type,
        is_active=symbol.is_active,
    )


@router.put("/{symbol_id}", response_model=SymbolResponse)
def update_symbol(
    symbol_id: int,
    symbol: SymbolCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = SymbolService(db)

    updated_symbol = service.update_symbol(
        symbol_id=symbol_id,
        ticker=symbol.ticker,
        display_name=symbol.display_name,
        asset_type=symbol.asset_type,
        is_active=symbol.is_active,
    )

    if not updated_symbol:
        raise HTTPException(
            status_code=404,
            detail="Symbol not found",
        )

    return updated_symbol


@router.delete("/{symbol_id}")
def delete_symbol(
    symbol_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = SymbolService(db)

    success = service.delete_symbol(symbol_id)

    if not success:
        raise HTTPException(
            status_code=404,
            detail="Symbol not found",
        )

    return {
        "message": "Symbol deleted successfully",
    }

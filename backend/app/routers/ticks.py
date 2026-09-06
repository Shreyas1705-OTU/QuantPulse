from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database.session import get_db
from app.schemas.tick import (
    TickCreate,
    TickResponse,
)
from app.services.tick_service import TickService

router = APIRouter(
    prefix="/ticks",
    tags=["Ticks"],
)


@router.post(
    "",
    response_model=TickResponse,
    status_code=201,
)
def create_tick(
    tick: TickCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TickService(db)

    return service.create_tick(
        symbol_id=tick.symbol_id,
        price=tick.price,
        volume=tick.volume,
        traded_at=tick.traded_at,
    )


@router.get(
    "",
    response_model=list[TickResponse],
)
def get_all_ticks(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TickService(db)

    return service.get_all_ticks()


@router.get(
    "/symbol/{symbol_id}",
    response_model=list[TickResponse],
)
def get_symbol_ticks(
    symbol_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TickService(db)

    return service.get_ticks_for_symbol(
        symbol_id
    )

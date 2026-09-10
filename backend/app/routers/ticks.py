from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.cache import cache_get, cache_set
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
    "/count",
)
def get_tick_count(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TickService(db)

    return {"count": service.count_ticks()}


@router.get(
    "",
    response_model=list[TickResponse],
)
def get_all_ticks(
    limit: int = Query(50, ge=1, le=500),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TickService(db)

    return service.get_all_ticks(limit=limit)


@router.get(
    "/latest",
    response_model=list[TickResponse],
)
def get_latest_ticks(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Cache-aside, 5s TTL -- matches the frontend's old poll cadence.
    # With the WS push in place this is now mostly a first-load / plain
    # REST-client cost saver rather than the primary path, but it's cheap
    # insurance either way.
    cache_key = "ticks:latest"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    service = TickService(db)
    ticks = service.get_latest_tick_per_symbol()

    data = [TickResponse.model_validate(t).model_dump(mode="json") for t in ticks]
    cache_set(cache_key, data, ttl_seconds=5)

    return data


@router.get(
    "/symbol/{symbol_id}",
    response_model=list[TickResponse],
)
def get_symbol_ticks(
    symbol_id: int,
    limit: int = Query(200, ge=1, le=1000),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TickService(db)

    return service.get_ticks_for_symbol(
        symbol_id,
        limit=limit,
    )

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database.session import get_db
from app.schemas.alert import AlertResponse
from app.services.alert_service import AlertService

router = APIRouter(
    prefix="/alerts",
    tags=["Alerts"],
)


@router.get(
    "/count",
)
def get_alert_count(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AlertService(db)

    return {"count": service.count_alerts()}


@router.get(
    "",
    response_model=list[AlertResponse],
)
def get_all_alerts(
    limit: int = Query(50, ge=1, le=500),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AlertService(db)

    return service.get_all_alerts(limit=limit)


@router.get(
    "/symbol/{symbol_id}",
    response_model=list[AlertResponse],
)
def get_symbol_alerts(
    symbol_id: int,
    limit: int = Query(100, ge=1, le=1000),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AlertService(db)

    return service.get_alerts_for_symbol(
        symbol_id,
        limit=limit,
    )

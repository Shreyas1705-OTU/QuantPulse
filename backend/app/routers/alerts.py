from fastapi import APIRouter, Depends
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
    "",
    response_model=list[AlertResponse],
)
def get_all_alerts(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AlertService(db)

    return service.get_all_alerts()


@router.get(
    "/symbol/{symbol_id}",
    response_model=list[AlertResponse],
)
def get_symbol_alerts(
    symbol_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AlertService(db)

    return service.get_alerts_for_symbol(
        symbol_id
    )

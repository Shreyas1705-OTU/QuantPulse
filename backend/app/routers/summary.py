from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database.session import get_db
from app.schemas.summary import DailySummaryResponse, SymbolSummaryResponse
from app.services.summary_service import SummaryService

router = APIRouter(
    prefix="/summary",
    tags=["Summary"],
)


@router.get(
    "/today",
    response_model=DailySummaryResponse,
)
def get_today_summary(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = SummaryService(db)

    # Falls back to the latest cached summary if today's hasn't been
    # generated yet (e.g. before ai/daily_summary.py's scheduled run) --
    # still 404s if none exist at all rather than return nothing useful.
    summary = service.get_latest_summary()

    if not summary:
        raise HTTPException(
            status_code=404,
            detail="No summary generated yet",
        )

    return summary


@router.get(
    "/symbols",
    response_model=list[SymbolSummaryResponse],
)
def get_symbol_summaries(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # No 404 here, unlike /today -- an empty list (nothing generated yet
    # for any symbol) is a normal, renderable state, not an error.
    service = SummaryService(db)
    return service.get_symbol_summaries()

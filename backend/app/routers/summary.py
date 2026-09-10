from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.cache import cache_get, cache_set
from app.core.security import get_current_user
from app.database.session import get_db
from app.schemas.summary import DailySummaryResponse, SymbolSummaryResponse
from app.services.summary_service import SummaryService

# Both summaries only ever change on a CronJob's schedule (every 15 min
# for symbol summaries, once a day for the daily digest) -- a much longer
# TTL than ticks/latest's 5s is safe and cuts real load, since these are
# also the two endpoints SummaryService hits with the heaviest queries
# (a join, for symbol summaries).
SUMMARY_TTL_SECONDS = 60

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
    cache_key = "summary:today"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

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

    data = DailySummaryResponse.model_validate(summary).model_dump(mode="json")
    cache_set(cache_key, data, ttl_seconds=SUMMARY_TTL_SECONDS)

    return data


@router.get(
    "/symbols",
    response_model=list[SymbolSummaryResponse],
)
def get_symbol_summaries(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cache_key = "summary:symbols"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    # No 404 here, unlike /today -- an empty list (nothing generated yet
    # for any symbol) is a normal, renderable state, not an error.
    service = SummaryService(db)
    rows = service.get_symbol_summaries()

    data = [
        SymbolSummaryResponse.model_validate(r).model_dump(mode="json")
        for r in rows
    ]
    cache_set(cache_key, data, ttl_seconds=SUMMARY_TTL_SECONDS)

    return data

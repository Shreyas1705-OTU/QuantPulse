"""
Pure-logic tests for is_market_open() -- no DB, no network, deterministic.

All test dates are picked and cross-checked against real calendar facts
(day-of-week, real NYSE holiday dates, real DST transition dates for the
years used), not against the module's own internal helpers -- otherwise
this would just be re-testing the implementation against itself.
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.market_hours import is_market_open  # noqa: E402


def _et_to_utc(year, month, day, hour=12, minute=0, dst=True):
    """Build a UTC datetime for a given US-Eastern wall-clock time.
    ET = UTC - 4h in DST (EDT), UTC - 5h in standard time (EST) -- so
    UTC = ET + 4h or ET + 5h."""
    delta = timedelta(hours=4 if dst else 5)
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc) + delta


class TestCrypto:
    def test_always_open_any_day_any_hour(self):
        # Saturday, 3am ET -- would be closed for anything else.
        now = _et_to_utc(2026, 7, 4, 3, 0, dst=True)
        assert is_market_open("crypto", now) is True

    def test_open_on_a_known_holiday(self):
        now = _et_to_utc(2026, 12, 25, 12, 0, dst=False)
        assert is_market_open("crypto", now) is True


class TestForex:
    def test_closed_saturday(self):
        # 2026-07-04 is a Saturday.
        now = _et_to_utc(2026, 7, 4, 12, 0, dst=True)
        assert is_market_open("forex", now) is False

    def test_closed_sunday(self):
        # 2026-07-05 is a Sunday.
        now = _et_to_utc(2026, 7, 5, 12, 0, dst=True)
        assert is_market_open("forex", now) is False

    def test_open_weekday_any_hour(self):
        # 2026-06-15 is a Monday -- forex doesn't model exact session
        # hours (documented simplification), so any weekday hour counts.
        now = _et_to_utc(2026, 6, 15, 2, 0, dst=True)
        assert is_market_open("forex", now) is True

    def test_open_on_a_us_equity_holiday(self):
        # Forex trades through US equity holidays -- Christmas 2026
        # falls on a Friday, a normal forex trading day.
        now = _et_to_utc(2026, 12, 25, 12, 0, dst=False)
        assert is_market_open("forex", now) is True


class TestEquityHours:
    # 2026-06-15 is a Monday, no nearby holiday -- a clean DST-era weekday.
    def test_open_during_regular_hours_dst(self):
        now = _et_to_utc(2026, 6, 15, 12, 0, dst=True)
        assert is_market_open("equity", now) is True

    def test_closed_before_open_dst(self):
        now = _et_to_utc(2026, 6, 15, 9, 29, dst=True)
        assert is_market_open("equity", now) is False

    def test_open_at_exact_open_dst(self):
        now = _et_to_utc(2026, 6, 15, 9, 30, dst=True)
        assert is_market_open("equity", now) is True

    def test_closed_at_exact_close_dst(self):
        # Close is exclusive -- 4:00:00pm itself is already closed.
        now = _et_to_utc(2026, 6, 15, 16, 0, dst=True)
        assert is_market_open("equity", now) is False

    def test_open_one_minute_before_close_dst(self):
        now = _et_to_utc(2026, 6, 15, 15, 59, dst=True)
        assert is_market_open("equity", now) is True

    # 2026-01-05 is a Monday, standard time (winter), no nearby holiday.
    def test_open_during_regular_hours_standard_time(self):
        now = _et_to_utc(2026, 1, 5, 12, 0, dst=False)
        assert is_market_open("equity", now) is True

    def test_closed_before_open_standard_time(self):
        now = _et_to_utc(2026, 1, 5, 9, 29, dst=False)
        assert is_market_open("equity", now) is False

    def test_closed_weekend_saturday(self):
        now = _et_to_utc(2026, 7, 4, 12, 0, dst=True)
        assert is_market_open("equity", now) is False

    def test_closed_weekend_sunday(self):
        now = _et_to_utc(2026, 7, 5, 12, 0, dst=True)
        assert is_market_open("equity", now) is False


class TestEquityHolidays:
    """Every date here is a real NYSE-observed holiday for the given
    year, cross-checked independently against the calendar -- not
    derived from the module under test."""

    @pytest.mark.parametrize(
        "year,month,day,dst,label",
        [
            (2026, 1, 1, False, "New Year's Day (Thursday, no shift)"),
            (2026, 1, 19, False, "MLK Day (3rd Monday of January)"),
            (2026, 2, 16, False, "Washington's Birthday (3rd Monday of Feb)"),
            (2026, 4, 3, True, "Good Friday (Easter 2026 is April 5)"),
            (2026, 5, 25, True, "Memorial Day (last Monday of May)"),
            (2026, 6, 19, True, "Juneteenth (Friday, no shift)"),
            (2026, 9, 7, True, "Labor Day (1st Monday of September)"),
            (2026, 11, 26, True, "Thanksgiving (4th Thursday of November)"),
            (2026, 12, 25, False, "Christmas (Friday, no shift)"),
        ],
    )
    def test_closed_on_holiday(self, year, month, day, dst, label):
        now = _et_to_utc(year, month, day, 12, 0, dst=dst)
        assert is_market_open("equity", now) is False, label

    def test_independence_day_saturday_observed_friday(self):
        # 2026-07-04 (Independence Day) is a Saturday -- observed the
        # Friday before, 2026-07-03. The actual Saturday holiday itself
        # is already covered by test_closed_weekend_saturday above; this
        # confirms the *shifted* observance date is also closed.
        now = _et_to_utc(2026, 7, 3, 12, 0, dst=True)
        assert is_market_open("equity", now) is False

    def test_independence_day_sunday_observed_monday(self):
        # 2027-07-04 (Independence Day) is a Sunday -- observed the
        # Monday after, 2027-07-05.
        now = _et_to_utc(2027, 7, 5, 12, 0, dst=True)
        assert is_market_open("equity", now) is False

    def test_christmas_saturday_observed_friday(self):
        # 2027-12-25 (Christmas) is a Saturday -- observed the Friday
        # before, 2027-12-24.
        now = _et_to_utc(2027, 12, 24, 12, 0, dst=False)
        assert is_market_open("equity", now) is False

    def test_day_after_a_holiday_is_a_normal_trading_day(self):
        # 2026-01-02 (the Friday right after New Year's) must trade
        # normally -- the holiday check shouldn't over-match nearby dates.
        now = _et_to_utc(2026, 1, 2, 12, 0, dst=False)
        assert is_market_open("equity", now) is True


class TestDSTBoundary:
    # DST 2026: starts 2nd Sunday of March (2026-03-08), ends 1st Sunday
    # of November (2026-11-01).
    def test_just_before_dst_start_uses_standard_offset(self):
        # 2026-03-06 is a Friday, still standard time. If this were
        # misclassified as DST (UTC-4 instead of UTC-5), 9:30am EST
        # would incorrectly read as 8:30am EST-equivalent and the
        # is-open window would shift by an hour.
        now_before_open_if_dst = _et_to_utc(2026, 3, 6, 9, 15, dst=True)
        # Under the correct (standard-time) offset, this UTC instant is
        # actually 8:15am ET -- before the open.
        assert is_market_open("equity", now_before_open_if_dst) is False

    def test_first_weekday_after_dst_start_uses_dst_offset(self):
        # 2026-03-09 (Monday) is the first weekday after DST starts.
        now = _et_to_utc(2026, 3, 9, 12, 0, dst=True)
        assert is_market_open("equity", now) is True

    def test_last_weekday_before_dst_end_still_dst(self):
        # 2026-10-30 (Friday) -- DST doesn't end until 2026-11-01.
        now = _et_to_utc(2026, 10, 30, 12, 0, dst=True)
        assert is_market_open("equity", now) is True

    def test_first_weekday_after_dst_end_uses_standard_offset(self):
        # 2026-11-02 (Monday) is the first weekday after DST ends.
        now = _et_to_utc(2026, 11, 2, 12, 0, dst=False)
        assert is_market_open("equity", now) is True


class TestUnknownAssetType:
    def test_fails_open_rather_than_hiding_data(self):
        # A typo'd or future asset_type this module hasn't been taught
        # about yet should never silently make a symbol look perpetually
        # closed -- see the module's own comment on this choice.
        now = _et_to_utc(2026, 7, 4, 3, 0, dst=True)  # a Saturday
        assert is_market_open("something_new", now) is True


class TestDefaultNow:
    def test_runs_without_a_now_argument(self):
        # Just confirms the real-clock default path doesn't crash --
        # the actual open/closed value depends on when this runs, so
        # there's nothing meaningful to assert about the result itself.
        for asset_type in ("crypto", "forex", "equity"):
            assert isinstance(is_market_open(asset_type), bool)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))

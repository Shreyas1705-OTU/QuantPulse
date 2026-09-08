"""
Market-hours awareness, per asset_type.

- crypto: always open (24/7).
- forex: closed Saturday and all of Sunday. A real forex week actually
  runs ~Sunday 5pm ET to Friday 5pm ET, not a clean day boundary -- this
  is a deliberate simplification (documented, not hidden) rather than
  modeling session opens across time zones for a feature whose whole job
  is "should the dashboard say markets are closed."
- equity: NYSE regular hours only -- 9:30am-4:00pm Eastern, Mon-Fri,
  minus NYSE holidays.

NYSE holidays are computed from the standard observance rules (nth-weekday
holidays, the Gregorian Easter algorithm for Good Friday, and the
Saturday-before/Sunday-after shift for fixed-date holidays) for whatever
year is asked about -- not a hardcoded list that goes stale every January.

US Eastern time is derived by hand (fixed UTC-5/-4 offset, US DST rules)
rather than via zoneinfo, so this doesn't depend on the container image
having a full IANA tzdata install.
"""

from datetime import date, datetime, timedelta, timezone


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """The nth occurrence of `weekday` (Monday=0) in the given month."""
    d = date(year, month, 1)
    offset = (weekday - d.weekday()) % 7
    return d + timedelta(days=offset + 7 * (n - 1))


def _last_weekday(year: int, month: int, weekday: int) -> date:
    """The last occurrence of `weekday` in the given month."""
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)
    offset = (last_day.weekday() - weekday) % 7
    return last_day - timedelta(days=offset)


def _easter(year: int) -> date:
    """Easter Sunday, Gregorian algorithm (Anonymous/Meeus)."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def _observed(d: date) -> date:
    """NYSE Saturday-before/Sunday-after shift for a fixed-date holiday."""
    if d.weekday() == 5:  # Saturday
        return d - timedelta(days=1)
    if d.weekday() == 6:  # Sunday
        return d + timedelta(days=1)
    return d


def _nyse_holidays(year: int) -> set:
    return {
        _observed(date(year, 1, 1)),         # New Year's Day
        _nth_weekday(year, 1, 0, 3),          # MLK Day
        _nth_weekday(year, 2, 0, 3),          # Washington's Birthday
        _easter(year) - timedelta(days=2),    # Good Friday
        _last_weekday(year, 5, 0),            # Memorial Day
        _observed(date(year, 6, 19)),         # Juneteenth
        _observed(date(year, 7, 4)),          # Independence Day
        _nth_weekday(year, 9, 0, 1),          # Labor Day
        _nth_weekday(year, 11, 3, 4),         # Thanksgiving
        _observed(date(year, 12, 25)),        # Christmas
    }


def _is_us_dst(d: date) -> bool:
    """US DST: 2nd Sunday of March through 1st Sunday of November."""
    dst_start = _nth_weekday(d.year, 3, 6, 2)
    dst_end = _nth_weekday(d.year, 11, 6, 1)
    return dst_start <= d < dst_end


def _to_eastern(now_utc: datetime) -> datetime:
    offset_hours = -4 if _is_us_dst(now_utc.date()) else -5
    return now_utc + timedelta(hours=offset_hours)


def is_market_open(asset_type: str, now: datetime = None) -> bool:
    """
    Whether `asset_type` is currently trading. `now` defaults to the real
    current time (UTC); accepting it as a parameter keeps this testable
    without patching the clock.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    if asset_type == "crypto":
        return True

    eastern = _to_eastern(now)
    weekday = eastern.weekday()  # Monday=0 ... Sunday=6

    if asset_type == "forex":
        return weekday not in (5, 6)  # closed Sat/Sun, see module docstring

    if asset_type == "equity":
        if weekday >= 5:
            return False
        if eastern.date() in _nyse_holidays(eastern.year):
            return False
        market_open = eastern.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = eastern.replace(hour=16, minute=0, second=0, microsecond=0)
        return market_open <= eastern < market_close

    # Unknown asset_type -- fail open rather than silently hide a symbol's
    # data over a typo/future asset type this hasn't been taught about yet.
    return True

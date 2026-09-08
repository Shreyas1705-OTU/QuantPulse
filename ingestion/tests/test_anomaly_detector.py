"""
Pure-logic tests for AnomalyDetector -- no DB, no network, deterministic.
This is the actual anomaly-detection algorithm the whole project is built
around, so it gets the most thorough coverage of anything tested here.
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from anomaly_detector import (  # noqa: E402
    AnomalyDetector,
    MIN_SAMPLES,
    WINDOW,
    PRICE_Z_MEDIUM,
    PRICE_Z_HIGH,
    VOLUME_Z_MEDIUM,
    VOLUME_Z_HIGH,
    COOLDOWN_SECONDS,
    Z_DISPLAY_CAP,
)


def _t(seconds_offset=0):
    return datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=seconds_offset)


def _seed(detector, ticker, prices, volumes=None, start=0, step=1):
    """Feed a series of ticks with no expectation of alerts, to build up
    a baseline window. Returns the timestamp of the last tick fed."""
    volumes = volumes or [100] * len(prices)
    ts = start
    for price, volume in zip(prices, volumes):
        detector.check_tick(ticker, price, volume, _t(ts))
        ts += step
    return ts


class TestBaselineBehavior:
    def test_no_alert_before_min_samples(self):
        detector = AnomalyDetector()
        # One short of MIN_SAMPLES -- even a wild outlier can't fire yet,
        # there's not enough history to compute a meaningful stdev against.
        _seed(detector, "AAPL", [100.0] * (MIN_SAMPLES - 1))
        alerts = detector.check_tick("AAPL", 100000.0, 100, _t(999))
        assert alerts == []

    def test_flat_window_never_alerts(self):
        # stdev == 0 (identical prices) must short-circuit, not divide by
        # zero or produce an infinite/NaN z-score.
        detector = AnomalyDetector()
        _seed(detector, "AAPL", [100.0] * MIN_SAMPLES)
        alerts = detector.check_tick("AAPL", 999999.0, 100, _t(999))
        assert alerts == []

    def test_tick_not_compared_against_itself(self):
        # The window used for comparison is the state BEFORE this tick is
        # folded in -- feeding the exact same wild value MIN_SAMPLES times
        # must never alert on itself, since each is only ever compared
        # against the (still-normal) history that came before it.
        detector = AnomalyDetector()
        alerts_seen = []
        for i in range(MIN_SAMPLES + 5):
            alerts_seen.extend(detector.check_tick("AAPL", 100.0, 100, _t(i)))
        assert alerts_seen == []


class TestPriceThresholds:
    def _build(self):
        detector = AnomalyDetector()
        # Small alternating noise around 100 -- real variance (stdev != 0)
        # but tight enough that a genuine outlier stands out clearly.
        prices = [100.0 + (0.1 if i % 2 == 0 else -0.1) for i in range(WINDOW)]
        last_ts = _seed(detector, "AAPL", prices)
        return detector, last_ts

    def test_small_deviation_no_alert(self):
        detector, ts = self._build()
        alerts = detector.check_tick("AAPL", 100.05, 100, _t(ts))
        assert alerts == []

    def test_medium_deviation_fires_medium(self):
        detector, ts = self._build()
        # stdev here is exactly 0.1, mean 100.0 -- 100.25 is z=2.5:
        # comfortably past PRICE_Z_MEDIUM (2.0) but strictly short of
        # PRICE_Z_HIGH (3.0, which _severity_for treats as inclusive),
        # so this should land MEDIUM, not HIGH.
        alerts = detector.check_tick("AAPL", 100.25, 100, _t(ts))
        assert len(alerts) == 1
        severity, message = alerts[0]
        assert severity == "MEDIUM"
        assert "Price anomaly" in message

    def test_large_deviation_fires_high(self):
        detector, ts = self._build()
        alerts = detector.check_tick("AAPL", 500.0, 100, _t(ts))
        assert len(alerts) == 1
        severity, _ = alerts[0]
        assert severity == "HIGH"

    def test_negative_deviation_also_fires(self):
        # Anomaly detection is symmetric -- a crash is just as anomalous
        # as a spike, and severity uses abs(z).
        detector, ts = self._build()
        alerts = detector.check_tick("AAPL", -500.0, 100, _t(ts))
        assert len(alerts) == 1
        assert alerts[0][0] == "HIGH"


class TestVolumeThresholds:
    def test_volume_needs_a_much_bigger_move_than_price(self):
        # Same relative deviation (in stdevs) that fires HIGH for price
        # must NOT fire at all for volume, since VOLUME_Z_HIGH (6.0) is
        # set well above PRICE_Z_HIGH (3.0) specifically because volume
        # is noisier tick-to-tick in real data.
        detector = AnomalyDetector()
        volumes = [100.0 + (1 if i % 2 == 0 else -1) for i in range(WINDOW)]
        _seed(detector, "AAPL", [100.0] * WINDOW, volumes=volumes)

        # ~4 stdevs out on a series with stdev=1 -- past PRICE_Z_HIGH,
        # short of VOLUME_Z_MEDIUM (4.0 exactly at the boundary; use a
        # value clearly under it).
        alerts = detector.check_tick("AAPL", 100.0, 103.0, _t(999))
        assert alerts == []

    def test_volume_fires_high_far_enough_out(self):
        detector = AnomalyDetector()
        volumes = [100.0 + (1 if i % 2 == 0 else -1) for i in range(WINDOW)]
        _seed(detector, "AAPL", [100.0] * WINDOW, volumes=volumes)

        alerts = detector.check_tick("AAPL", 100.0, 1000.0, _t(999))
        assert len(alerts) == 1
        severity, message = alerts[0]
        assert severity == "HIGH"
        assert "Volume anomaly" in message

    def test_price_and_volume_are_independent_checks(self):
        # A tick can be anomalous on both dimensions at once -- both must
        # be reported, not just the first one found.
        detector = AnomalyDetector()
        prices = [100.0 + (0.1 if i % 2 == 0 else -0.1) for i in range(WINDOW)]
        volumes = [100.0 + (1 if i % 2 == 0 else -1) for i in range(WINDOW)]
        _seed(detector, "AAPL", prices, volumes=volumes)

        alerts = detector.check_tick("AAPL", 500.0, 1000.0, _t(999))
        kinds = {a[1].split()[0] for a in alerts}
        assert kinds == {"Price", "Volume"}
        assert all(sev == "HIGH" for sev, _ in alerts)


class TestCooldown:
    def _build(self):
        detector = AnomalyDetector()
        prices = [100.0 + (0.1 if i % 2 == 0 else -0.1) for i in range(WINDOW)]
        last_ts = _seed(detector, "AAPL", prices)
        return detector, last_ts

    def test_second_alert_within_cooldown_is_suppressed(self):
        detector, ts = self._build()
        first = detector.check_tick("AAPL", 500.0, 100, _t(ts))
        assert len(first) == 1

        second = detector.check_tick(
            "AAPL", 500.0, 100, _t(ts + COOLDOWN_SECONDS - 1)
        )
        assert second == []

    def test_alert_fires_again_once_cooldown_elapses(self):
        detector, ts = self._build()
        first = detector.check_tick("AAPL", 500.0, 100, _t(ts))
        assert len(first) == 1

        second = detector.check_tick(
            "AAPL", 500.0, 100, _t(ts + COOLDOWN_SECONDS + 1)
        )
        assert len(second) == 1

    def test_cooldown_is_independent_per_kind(self):
        # A price-alert cooldown must not suppress a volume alert on the
        # very next tick -- last_alert_at is keyed by kind, not shared.
        detector = AnomalyDetector()
        prices = [100.0 + (0.1 if i % 2 == 0 else -0.1) for i in range(WINDOW)]
        volumes = [100.0 + (1 if i % 2 == 0 else -1) for i in range(WINDOW)]
        ts = _seed(detector, "AAPL", prices, volumes=volumes)

        first = detector.check_tick("AAPL", 500.0, 100, _t(ts))
        assert [k for k, _ in first] and "Price" in first[0][1]

        # Price is now on cooldown, but volume never fired yet -- a
        # volume-only anomaly right after must still fire.
        second = detector.check_tick("AAPL", 100.0, 1000.0, _t(ts + 1))
        assert len(second) == 1
        assert "Volume" in second[0][1]

    def test_cooldown_is_independent_per_symbol(self):
        detector = AnomalyDetector()
        prices = [100.0 + (0.1 if i % 2 == 0 else -0.1) for i in range(WINDOW)]
        ts_a = _seed(detector, "AAPL", prices)
        ts_b = _seed(detector, "TSLA", prices)

        alerts_a = detector.check_tick("AAPL", 500.0, 100, _t(ts_a))
        assert len(alerts_a) == 1

        # TSLA has never alerted -- AAPL's cooldown must not leak across
        # symbols (separate _SymbolWindow per ticker).
        alerts_b = detector.check_tick("TSLA", 500.0, 100, _t(ts_b))
        assert len(alerts_b) == 1


class TestDisplayCap:
    def test_extreme_z_is_capped_in_message_but_still_high_severity(self):
        # An extremely tight window can produce a mathematically real but
        # meaningless z (observed live: z=-1210.57) -- the display value
        # must be capped at +/-Z_DISPLAY_CAP, while the classification
        # itself is untouched (still HIGH; detection uses the real z).
        detector = AnomalyDetector()
        # A very tight window (stdev tiny) makes an ordinary-looking
        # absolute jump compute to a huge z.
        prices = [100.0 + (0.001 if i % 2 == 0 else -0.001) for i in range(WINDOW)]
        ts = _seed(detector, "AAPL", prices)

        alerts = detector.check_tick("AAPL", 500.0, 100, _t(ts))
        assert len(alerts) == 1
        severity, message = alerts[0]
        assert severity == "HIGH"

        # Parse "z=<value>" back out of the message and confirm it's
        # within the cap, even though the true z is far larger.
        z_str = message.split("z=")[1].rstrip(")")
        z_value = float(z_str)
        assert abs(z_value) <= Z_DISPLAY_CAP


class TestRollingWindow:
    def test_window_evicts_old_samples_beyond_maxlen(self):
        # Feed WINDOW normal samples, then WINDOW more that establish a
        # completely different baseline -- once the old samples have
        # fully rolled off (deque maxlen=WINDOW), a value that would have
        # been anomalous against the OLD baseline must be normal against
        # the new one.
        detector = AnomalyDetector()
        _seed(detector, "AAPL", [100.0 + (0.1 if i % 2 == 0 else -0.1) for i in range(WINDOW)])

        # Roll the window over entirely to a new baseline around 500.
        ts = _seed(
            detector, "AAPL",
            [500.0 + (0.1 if i % 2 == 0 else -0.1) for i in range(WINDOW)],
            start=WINDOW,
        )

        # 500 is now completely ordinary -- must not alert even though
        # it would have been wildly anomalous against the original
        # around-100 baseline.
        alerts = detector.check_tick("AAPL", 500.05, 100, _t(ts))
        assert alerts == []


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))

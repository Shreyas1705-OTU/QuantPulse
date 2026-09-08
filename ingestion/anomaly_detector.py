"""
Rolling z-score anomaly detection on price/volume, per symbol.

Runs entirely in-memory inside the ingestion process -- deliberately not a
separate service, since anything that needs to see every tick for a symbol
in order has to be this same single-replica process anyway (see the
replicas: 1 comment in k8s/ingestion/deployment.yaml).

For each symbol, keeps a rolling window of the last WINDOW ticks' price and
volume. Once there's enough history (MIN_SAMPLES), a new value is compared
against the window's mean/stdev; a large enough deviation is an anomaly.
This is a z-score test, which is the same shape as a Bollinger Band check
(mean +/- k*stdev) -- just framed as "how many stdevs away" instead of
"which band".

Deliberately does NOT generate an LLM explanation here -- that's a separate,
later step (see Alert.message below), so a slow/failed external API call
can never block the real-time tick loop this runs inside.
"""

import statistics
from collections import defaultdict, deque

WINDOW = 30           # rolling sample size per symbol
MIN_SAMPLES = 20      # don't flag anything until there's enough history

# Volume varies far more tick-to-tick than price does -- any single
# trade's size is close to independent of the last one, so a shared
# threshold made volume fire on ordinary variance almost constantly in
# practice (observed: 75+ alerts/day, nearly all small BTCUSDT/EUR_USD
# volume blips). Price keeps the original bar; volume needs a much
# higher one before it means anything.
PRICE_Z_MEDIUM = 2.0
PRICE_Z_HIGH = 3.0
VOLUME_Z_MEDIUM = 4.0
VOLUME_Z_HIGH = 6.0

# Per symbol, per kind. Raised from 60s -- even with the higher volume
# bar above, a genuinely volatile stretch could still refire every
# window; 5 minutes keeps alerts meaningful without needing a fully
# different (e.g. exponential backoff) suppression scheme.
COOLDOWN_SECONDS = 300


class _SymbolWindow:
    def __init__(self):
        self.prices = deque(maxlen=WINDOW)
        self.volumes = deque(maxlen=WINDOW)
        self.last_alert_at = {}  # kind ("price"/"volume") -> datetime


def _severity_for(z, z_medium, z_high):
    az = abs(z)
    if az >= z_high:
        return "HIGH"
    if az >= z_medium:
        return "MEDIUM"
    return None


class AnomalyDetector:
    def __init__(self):
        self._windows = defaultdict(_SymbolWindow)

    def check_tick(self, ticker, price, volume, traded_at):
        """
        Compares `price`/`volume` against ticker's rolling history (BEFORE
        folding this tick in, so a tick is never compared against itself),
        then updates the window. Returns a list of (severity, message)
        tuples -- empty if nothing anomalous.
        """
        window = self._windows[ticker]
        alerts = []

        for value, series, kind, label, z_medium, z_high in (
            (price, window.prices, "price", "Price", PRICE_Z_MEDIUM, PRICE_Z_HIGH),
            (volume, window.volumes, "volume", "Volume", VOLUME_Z_MEDIUM, VOLUME_Z_HIGH),
        ):
            alert = self._check_series(
                series, value, kind, label, z_medium, z_high,
                traded_at, window.last_alert_at,
            )
            if alert:
                alerts.append(alert)

        window.prices.append(price)
        window.volumes.append(volume)

        return alerts

    @staticmethod
    def _check_series(series, value, kind, label, z_medium, z_high, now, last_alert_at):
        if len(series) < MIN_SAMPLES:
            return None

        mean = statistics.mean(series)
        stdev = statistics.pstdev(series)

        if stdev == 0:
            # Flat window (e.g. a quiet market) -- any deviation would
            # produce an infinite/undefined z-score. Nothing to flag.
            return None

        z = (value - mean) / stdev
        severity = _severity_for(z, z_medium, z_high)

        if severity is None:
            return None

        last = last_alert_at.get(kind)
        if last is not None and (now - last).total_seconds() < COOLDOWN_SECONDS:
            return None

        last_alert_at[kind] = now

        message = f"{label} anomaly: {value:.4f} vs avg {mean:.4f} (z={z:.2f})"
        return severity, message

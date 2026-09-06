from prometheus_client import Counter

# Total number of ticks ingested
TICKS_TOTAL = Counter(
    "quantpulse_ticks_total",
    "Total market ticks ingested",
)

# Total alerts generated
ALERTS_TOTAL = Counter(
    "quantpulse_alerts_total",
    "Total alerts generated",
)

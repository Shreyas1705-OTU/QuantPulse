from prometheus_client import Counter

# Total alerts generated
ALERTS_TOTAL = Counter(
    "quantpulse_alerts_total",
    "Total alerts generated",
)

# Note: "ticks ingested" lives in the ingestion service's own /metrics
# endpoint (quantpulse_ticks_ingested_total), not here -- the backend
# never touches those writes, since ingestion writes directly to
# Postgres. See ingestion/finnhub_ingestion.py.

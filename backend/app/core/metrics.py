# Both "ticks ingested" and "alerts generated" live in the ingestion
# service's own /metrics endpoint (quantpulse_ticks_ingested_total,
# quantpulse_alerts_total), not here -- the backend never touches those
# writes. Ticks are inserted directly by the Finnhub ingestion service,
# and alerts are created by its rolling anomaly detector -- the backend
# has no code path that creates either. See ingestion/finnhub_ingestion.py
# and ingestion/anomaly_detector.py.

from prometheus_client import Counter, Gauge

# Total number of readings received
READINGS_TOTAL = Counter(
    "quantpulse_readings_total",
    "Total sensor readings received",
)

# Total alerts generated
ALERTS_TOTAL = Counter(
    "quantpulse_alerts_total",
    "Total alerts generated",
)

# Latest sensor values
TEMPERATURE_GAUGE = Gauge(
    "quantpulse_temperature_celsius",
    "Latest temperature reading",
)

HUMIDITY_GAUGE = Gauge(
    "quantpulse_humidity_percent",
    "Latest humidity reading",
)

BATTERY_GAUGE = Gauge(
    "quantpulse_battery_percent",
    "Latest battery percentage",
)
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, make_asgi_app

from app.core.config import settings
from app.routers.auth import router as auth_router
from app.routers.symbols import router as symbol_router
from app.routers.ticks import router as tick_router
from app.routers.alerts import router as alert_router
from app.routers.summary import router as summary_router
from app.routers.stream import router as stream_router

app = FastAPI(
    title=settings.APP_NAME,
    description="Real-time, AI-assisted market monitoring platform",
    version=settings.APP_VERSION,
)

# -----------------------------
# CORS Configuration
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Prometheus Metrics Endpoint
# -----------------------------
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

HTTP_REQUESTS_TOTAL = Counter(
    "quantpulse_http_requests_total",
    "Total HTTP requests handled by the backend",
    ["method", "path", "status"],
)
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "quantpulse_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "path"],
)


@app.middleware("http")
async def prometheus_request_metrics(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start

    # The matched route's own path template (e.g.
    # "/api/v1/ticks/symbol/{symbol_id}"), not the raw request path --
    # using the raw path would mean a distinct label value per symbol_id
    # ever requested, growing this metric's cardinality without bound as
    # more symbols/users/etc. get added. Falls back to the raw path for
    # anything that didn't match a route (a plain 404).
    route = request.scope.get("route")
    path = route.path if route is not None else request.url.path

    HTTP_REQUESTS_TOTAL.labels(
        method=request.method,
        path=path,
        status=response.status_code,
    ).inc()
    HTTP_REQUEST_DURATION_SECONDS.labels(
        method=request.method,
        path=path,
    ).observe(duration)

    return response

# -----------------------------
# Symbol APIs
# -----------------------------
app.include_router(
    symbol_router,
    prefix="/api/v1",
)

# -----------------------------
# Authentication APIs
# -----------------------------
app.include_router(
    auth_router,
    prefix="/api/v1/auth",
    tags=["Authentication"],
)

# -----------------------------
# Tick APIs
# -----------------------------
app.include_router(
    tick_router,
    prefix="/api/v1",
)

# -----------------------------
# Alert APIs
# -----------------------------
app.include_router(
    alert_router,
    prefix="/api/v1",
)

# -----------------------------
# Daily Summary APIs
# -----------------------------
app.include_router(
    summary_router,
    prefix="/api/v1",
)

# -----------------------------
# Live Push (WebSocket)
# -----------------------------
app.include_router(
    stream_router,
    prefix="/api/v1",
)

# -----------------------------
# Root Endpoint
# -----------------------------
@app.get("/")
def root():
    return {
        "application": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
        "status": "running",
        "message": "Welcome to QuantPulse!",
    }

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from app.core.config import settings
from app.routers.auth import router as auth_router
from app.routers.symbols import router as symbol_router
from app.routers.ticks import router as tick_router
from app.routers.alerts import router as alert_router
from app.routers.summary import router as summary_router

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

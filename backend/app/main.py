from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from app.core.config import settings
from app.routers.auth import router as auth_router
from app.routers.devices import router as device_router
from app.routers.readings import router as reading_router
from app.routers.alerts import router as alert_router

app = FastAPI(
    title=settings.APP_NAME,
    description="Cloud-native IoT Device Monitoring Platform",
    version=settings.APP_VERSION,
)

# -----------------------------
# CORS Configuration
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
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
# Device APIs
# -----------------------------
app.include_router(
    device_router,
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
# Sensor Reading APIs
# -----------------------------
app.include_router(
    reading_router,
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
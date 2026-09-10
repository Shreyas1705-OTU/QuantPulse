from dotenv import load_dotenv
import os

# Load environment variables from the .env file
load_dotenv()


class Settings:
    """
    Application configuration.
    Reads values from environment variables.
    """

    APP_NAME = os.getenv("APP_NAME", "QuantPulse")
    APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    DEBUG = os.getenv("DEBUG", "False") == "True"

    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql://quantpulse:quantpulse123@postgres:5432/quantpulse",
    )

    # Cache-aside reads (app/core/cache.py) and the pub/sub relay
    # (app/routers/stream.py) both go through this -- same service name
    # in-cluster (k8s/redis/service.yaml) and in docker-compose.
    REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

    # Signs/verifies JWTs (app/core/security.py). k8s provisions the real
    # value via quantpulse-secret -> JWT_SECRET_KEY (see k8s/secret.yaml);
    # this fallback only covers local dev without that secret set.
    JWT_SECRET_KEY = os.getenv(
        "JWT_SECRET_KEY",
        "change_this_to_a_long_random_secret_key",
    )

    # Comma-separated list of origins allowed to call the API via CORS.
    # Only matters for cross-origin calls (e.g. `npm run dev` on :5173
    # hitting the backend directly) -- in-cluster traffic goes through the
    # frontend's nginx /api/ same-origin proxy and never touches this.
    ALLOWED_ORIGINS = [
        origin.strip()
        for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
        if origin.strip()
    ]


# Create one global settings object
settings = Settings()
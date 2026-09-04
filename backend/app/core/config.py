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


# Create one global settings object
settings = Settings()
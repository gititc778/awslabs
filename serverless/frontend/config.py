"""Configuration for the ShopWave frontend (ECS / Python)."""
import os


class Config:
    # Base URL of the API Gateway that fronts the Lambda APIs.
    # e.g. https://abc123.execute-api.eu-west-2.amazonaws.com/prod
    API_BASE_URL = os.getenv("API_BASE_URL", "").rstrip("/")

    # How long (seconds) to wait on backend calls before giving up.
    API_TIMEOUT = float(os.getenv("API_TIMEOUT", "5"))

    # When no API_BASE_URL is configured, serve built-in sample data so the
    # UI is fully browsable during development. Set MOCK_MODE=false to force
    # real calls even without a URL (they will simply fail).
    MOCK_MODE = os.getenv("MOCK_MODE", "true").lower() in ("1", "true", "yes")

    # Flask session secret (used for flash messages).
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")

    # Store branding.
    STORE_NAME = os.getenv("STORE_NAME", "ShopWave")

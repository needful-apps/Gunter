"""Application configuration module."""

import os


class Config:
    """Central configuration class for the Gunter application."""

    # Database Configuration
    CUSTOM_DB_FILE = os.environ.get("GUNTER_DB_FILE")
    EXTERNAL_DB_URL = os.environ.get("GUNTER_DB_URL")
    DB_DIR = os.environ.get("GUNTER_DB_DIR", "/data")
    DB_FILE_PREFIX = "GeoLite2-City"
    DB_FILE_SUFFIX = ".mmdb"

    # MaxMind Configuration
    MAXMIND_LICENSE_KEY = os.environ.get("GUNTER_MAXMIND_LICENSE_KEY")
    MAXMIND_DOWNLOAD_URL = (
        f"https://download.maxmind.com/app/geoip_download?"
        f"edition_id=GeoLite2-City&license_key={MAXMIND_LICENSE_KEY}&suffix=tar.gz"
        if MAXMIND_LICENSE_KEY
        else None
    )

    # Language Configuration
    DEFAULT_LANG = os.environ.get("GUNTER_LANG", "de")

    # Server Configuration
    FLASK_HOST = "0.0.0.0"
    FLASK_PORT = 6600

    # Scheduler Configuration
    SCHEDULER_UPDATE_DAYS = 1

    # Feature Flags
    ENABLE_STATUS_ENDPOINT = (
        os.environ.get("GUNTER_ENABLE_STATUS", "true").lower() == "true"
    )
    ENABLE_API_DOCS = os.environ.get("GUNTER_ENABLE_API_DOCS", "true").lower() == "true"

    # CORS Configuration
    CORS_ORIGINS = os.environ.get("GUNTER_CORS_ORIGINS")

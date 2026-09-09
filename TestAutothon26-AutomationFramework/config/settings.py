"""Central, environment-driven configuration.

All values come from environment variables (loaded from .env), so no secret
is ever hard-coded in the repo.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

# --- directories ---
TEST_DATA_DIR = ROOT_DIR / "testdata"
REPORTS_DIR = ROOT_DIR / "reports"
SCREENSHOT_DIR = REPORTS_DIR / "screenshots"
DOWNLOAD_DIR = REPORTS_DIR / "downloads"
LOG_DIR = REPORTS_DIR / "logs"

for _d in (REPORTS_DIR, SCREENSHOT_DIR, DOWNLOAD_DIR, LOG_DIR):
    _d.mkdir(parents=True, exist_ok=True)


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes")


class Config:
    # --- application ---
    BASE_URL: str = os.getenv("BASE_URL", "https://stg.gajab.com").rstrip("/")
    DEFAULT_LANGUAGE: str = os.getenv("DEFAULT_LANGUAGE", "English")

    # --- credentials / test account ---
    MOBILE_NUMBER: str = os.getenv("TEST_MOBILE_NUMBER", "")
    OTP: str = os.getenv("DEFAULT_OTP", "123456")
    PINCODE: str = os.getenv("PINCODE", "560025")

    # --- browser ---
    BROWSER: str = os.getenv("BROWSER", "chrome").lower()
    HEADLESS: bool = _bool("HEADLESS", False)
    EXPLICIT_WAIT: int = int(os.getenv("EXPLICIT_WAIT", "25"))

    # --- email ---
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    EMAIL_TO: str = os.getenv("EMAIL_TO", "")

    # --- android ---
    APPIUM_SERVER_URL: str = os.getenv("APPIUM_SERVER_URL", "http://127.0.0.1:4723")
    ANDROID_UDID: str = os.getenv("ANDROID_UDID", "")
    ANDROID_PLATFORM_VERSION: str = os.getenv("ANDROID_PLATFORM_VERSION", "")
    ANDROID_APP_PACKAGE: str = os.getenv("ANDROID_APP_PACKAGE", "com.gajab.buyerstore")
    ANDROID_APP_ACTIVITY: str = os.getenv("ANDROID_APP_ACTIVITY", "")
    ANDROID_APP_PATH: str = os.getenv("ANDROID_APP_PATH", "")

    @classmethod
    def masked_mobile(cls) -> str:
        """Never print a full mobile number into logs or reports."""
        n = cls.MOBILE_NUMBER
        return f"{n[:2]}******{n[-2:]}" if len(n) >= 4 else "******"


config = Config()

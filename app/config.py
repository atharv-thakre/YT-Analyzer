import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


def _to_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _to_int(value: str, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_float(value: str, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Settings:
    database_url: str
    db_echo: bool
    youtube_api_key: str | None
    yt_api_timeout: float
    yt_api_retries: int
    freshness_default_hours: int
    freshness_min_hours: int
    freshness_max_hours: int


@lru_cache
def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv("DATABASE_URL"),
        db_echo=_to_bool(os.getenv("DB_ECHO", "false")),
        youtube_api_key=os.getenv("YOUTUBE_API_KEY"),
        yt_api_timeout=_to_float(os.getenv("YT_API_TIMEOUT", "15"), default=15.0),
        yt_api_retries=_to_int(os.getenv("YT_API_RETRIES", "3"), default=3),
        freshness_default_hours=_to_int(os.getenv("FRESHNESS_DEFAULT_HOURS", "24"), default=24),
        freshness_min_hours=_to_int(os.getenv("FRESHNESS_MIN_HOURS", "1"), default=1),
        freshness_max_hours=_to_int(os.getenv("FRESHNESS_MAX_HOURS", "168"), default=168),
    )


def validate_settings() -> list[str]:
    settings = get_settings()
    errors: list[str] = []

    if not settings.database_url:
        errors.append("DATABASE_URL is required.")

    if not settings.youtube_api_key:
        errors.append("YOUTUBE_API_KEY is required for analysis endpoints.")

    if settings.yt_api_timeout <= 0:
        errors.append("YT_API_TIMEOUT must be greater than 0.")

    if settings.yt_api_retries < 0:
        errors.append("YT_API_RETRIES must be >= 0.")

    if settings.freshness_min_hours < 1:
        errors.append("FRESHNESS_MIN_HOURS must be >= 1.")

    if settings.freshness_max_hours < settings.freshness_min_hours:
        errors.append("FRESHNESS_MAX_HOURS must be >= FRESHNESS_MIN_HOURS.")

    if not (settings.freshness_min_hours <= settings.freshness_default_hours <= settings.freshness_max_hours):
        errors.append("FRESHNESS_DEFAULT_HOURS must be between FRESHNESS_MIN_HOURS and FRESHNESS_MAX_HOURS.")

    return errors

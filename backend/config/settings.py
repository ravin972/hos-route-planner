"""Django settings, deliberately minimal (architecture.md section 4.6).

This is a stateless API: no database, no sessions, no auth, no admin, no static files. Everything
configurable comes from environment variables. A ``.env`` file in the backend directory is loaded
automatically for local development (real env vars take precedence). The module must import cleanly
with no database configured, because Vercel executes ``manage.py`` to discover the entrypoint.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

from django.core.exceptions import ImproperlyConfigured

# Load .env from the backend directory (real env vars take precedence)
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    return float(raw) if raw else default


BASE_DIR = Path(__file__).resolve().parent.parent


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_list(name: str, default: str) -> list[str]:
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


DEBUG = _env_bool("DJANGO_DEBUG", default=False)

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY is required when DJANGO_DEBUG is not true. "
            "For local development set DJANGO_DEBUG=true."
        )
    SECRET_KEY = "insecure-development-key-never-use-in-production"

ALLOWED_HOSTS = _env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

INSTALLED_APPS = [
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    "trips",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

# No app ever renders a Django template except drf-spectacular's bundled Swagger UI page
# (/api/docs/) -- APP_DIRS finds it inside the drf_spectacular package itself; nothing here scans
# a project-level templates/ directory (there isn't one, and there must never be a database-backed
# app relying on this stack -- AD-1).
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {},
    }
]

# No database (architecture.md AD-1). An empty mapping selects Django's dummy backend, so any
# accidental ORM use fails loudly instead of quietly creating a file.
DATABASES: dict[str, dict[str, object]] = {}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    # Without django.contrib.auth installed, DRF must not try to build an AnonymousUser.
    "UNAUTHENTICATED_USER": None,
    "UNAUTHENTICATED_TOKEN": None,
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "trips.api.errors.exception_handler",
    "DEFAULT_THROTTLE_CLASSES": [],  # each view opts in explicitly (trips/api/throttles.py)
    "DEFAULT_THROTTLE_RATES": {
        "plan": os.environ.get("THROTTLE_PLAN", "30/min"),
        "search": os.environ.get("THROTTLE_SEARCH", "120/min"),
    },
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Spotter HOS Planner API",
    "DESCRIPTION": "Trip planning and FMCSA-style driver-log generation (architecture.md 6)",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

CORS_ALLOWED_ORIGINS = _env_list("CORS_ALLOWED_ORIGINS", "http://localhost:5173")

# Django LocMemCache (architecture.md section 4.8): geocode/route caching is per-instance and
# best-effort on serverless -- polite to free tiers, never load-bearing for correctness.
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = False
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- application settings (architecture.md section 4.5) ---------------------------------------
AVG_TRUCK_SPEED_MPH = _env_float("AVG_TRUCK_SPEED_MPH", 55.0)
UPSTREAM_TIMEOUT_S = _env_float("UPSTREAM_TIMEOUT_S", 10.0)
LOG_CARRIER_NAME = os.environ.get("LOG_CARRIER_NAME", "")
LOG_MAIN_OFFICE = os.environ.get("LOG_MAIN_OFFICE", "")
LOG_HOME_TERMINAL = os.environ.get("LOG_HOME_TERMINAL", "")
LOG_TRUCK_NUMBER = os.environ.get("LOG_TRUCK_NUMBER", "")

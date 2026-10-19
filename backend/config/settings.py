"""Django settings. Every deploy-specific value comes from the environment (ADR 0004)."""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def env(name, default=None):
    return os.environ.get(name, default)


def env_bool(name, default=False):
    value = env(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name, default=""):
    return [item.strip() for item in env(name, default).split(",") if item.strip()]


# Safe by default: DEBUG is off unless explicitly switched on.
DEBUG = env_bool("DJANGO_DEBUG", default=False)

SECRET_KEY = env("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set.")

# Shared password of the local demo users, used only by the seed_demo command.
DEMO_USER_PASSWORD = env("DEMO_USER_PASSWORD", "")

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", "http://localhost:5173")

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "rest_framework",
    "accounts",
    "rooms",
    "bookings",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = []

# PostgreSQL only: the overlap guarantee depends on its exclusion constraints (ADR 0001).
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", "room_booking"),
        "USER": env("POSTGRES_USER", "postgres"),
        "PASSWORD": env("POSTGRES_PASSWORD", ""),
        "HOST": env("POSTGRES_HOST", "db"),
        "PORT": env("POSTGRES_PORT", "5432"),
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# The office runs on Doha time; the database stores UTC (ADR 0005).
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Qatar"
USE_I18N = False
USE_TZ = True

# Cookies (ADR 0004). The CSRF cookie stays readable so the SPA can send it back.
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = "Lax"

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# With DEBUG off the app assumes it is served over HTTPS (ADR 0004).
# includeSubDomains assumes any deployment controls every subdomain of its host.
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_AUTHENTICATION_CLASSES": ["accounts.authentication.ApiSessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "EXCEPTION_HANDLER": "config.exceptions.exception_handler",
    "DEFAULT_PAGINATION_CLASS": "config.pagination.StandardPagination",
    "DEFAULT_THROTTLE_RATES": {"login": "5/min"},
    # Exactly one trusted proxy hop: the Vite dev server appends the browser's
    # address to X-Forwarded-For, and DRF keys the login throttle on that last
    # entry, so each browser gets its own limit. Direct calls to port 8000 could
    # forge the header to dodge the limit (ADR 0004).
    "NUM_PROXIES": 1,
}

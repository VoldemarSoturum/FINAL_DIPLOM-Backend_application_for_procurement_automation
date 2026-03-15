# config/settings.py
from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

# -----------------------------------------------------------------------------
# Base
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DEBUG = os.getenv("DEBUG", "0") == "1"
SECRET_KEY = os.getenv("SECRET_KEY", "unsafe-dev-secret-key")
ALLOWED_HOSTS = ["*"]  # TODO: tighten in production

# ВАЖНО: Silk (и вообще Django auth redirects) используют LOGIN_URL
# По умолчанию Django ставит /accounts/login/, у нас такого роута нет.
LOGIN_URL = os.getenv("LOGIN_URL", "/admin/login/")

# -----------------------------------------------------------------------------
# Redis cache + ORM cache (Stage 9.6)
# -----------------------------------------------------------------------------
# В docker: redis://redis:6379/2
# Локально: redis://127.0.0.1:6379/2
REDIS_CACHE_URL = os.getenv("REDIS_CACHE_URL", "redis://127.0.0.1:6379/2")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_CACHE_URL,
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        "TIMEOUT": 60 * 60,  # 1 hour
    }
}

# Cachalot включаем/выключаем через env (удобно для замеров до/после)
CACHALOT_ENABLED = os.getenv("CACHALOT_ENABLED", "1") == "1"
CACHALOT_CACHE = "default"

# -----------------------------------------------------------------------------
# Feature toggles (Stage 9.7: Silk)
# -----------------------------------------------------------------------------
SILK_ENABLED = os.getenv("SILK_ENABLED", "0") == "1"

# -----------------------------------------------------------------------------
# Django apps
# -----------------------------------------------------------------------------
INSTALLED_APPS = [
    # Baton (must be BEFORE django.contrib.admin)
    "baton",

    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party
    "rest_framework",
    "drf_spectacular",
    "django_rest_passwordreset",

    # Local apps
    "apps.users.apps.UsersConfig",
    "apps.catalog.apps.CatalogConfig",
    "apps.orders",
    "apps.partners",

    # Social auth
    "social_django",

    # ORM cache
    "cachalot",

    # Baton autodiscover MUST be the last app (всегда последним!)
    "baton.autodiscover",
]

# Если Silk включён — добавляем его ДО baton.autodiscover (а baton.autodiscover оставляем последним)
if SILK_ENABLED:
    # вставим silk прямо перед последним элементом (baton.autodiscover)
    INSTALLED_APPS.insert(len(INSTALLED_APPS) - 1, "silk")

# -----------------------------------------------------------------------------
# Middleware
# -----------------------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",  # важен для OAuth state
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",

    # Social auth: graceful handling of OAuth exceptions (e.g. user canceled)
    "social_django.middleware.SocialAuthExceptionMiddleware",
]

# SilkyMiddleware должен быть максимально рано (чтобы перехватить всё)
if SILK_ENABLED:
    MIDDLEWARE = ["silk.middleware.SilkyMiddleware"] + MIDDLEWARE

ROOT_URLCONF = "config.urls"

# -----------------------------------------------------------------------------
# Templates
# -----------------------------------------------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # Social auth processors
                "social_django.context_processors.backends",
                "social_django.context_processors.login_redirect",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# -----------------------------------------------------------------------------
# Database
# -----------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB"),
        "USER": os.getenv("POSTGRES_USER"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD"),
        "HOST": os.getenv("POSTGRES_HOST", "127.0.0.1"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    }
}

# -----------------------------------------------------------------------------
# Password validation
# -----------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# -----------------------------------------------------------------------------
# I18N / TZ
# -----------------------------------------------------------------------------
LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True

# -----------------------------------------------------------------------------
# Static
# -----------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# -----------------------------------------------------------------------------
# Media (uploads)
# -----------------------------------------------------------------------------
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# -----------------------------------------------------------------------------
# Thumbnails / renditions (VersatileImageField)
# -----------------------------------------------------------------------------
VERSATILEIMAGEFIELD_SETTINGS = {"create_on_demand": False}

VERSATILEIMAGEFIELD_RENDITION_KEY_SETS = {
    "avatar": [
        ("full", "url"),
        ("sm", "thumbnail__64x64"),
        ("md", "thumbnail__256x256"),
        ("sq", "crop__128x128"),
    ],
    "product": [
        ("full", "url"),
        ("sm", "thumbnail__300x300"),
        ("md", "thumbnail__600x600"),
        ("sq", "crop__400x400"),
    ],
}

# -----------------------------------------------------------------------------
# DRF + OpenAPI
# -----------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.BasicAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    # Throttling (Stage 9.2)
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": os.getenv("DRF_THROTTLE_ANON", "1000/min"),
        "user": os.getenv("DRF_THROTTLE_USER", "1000/min"),
    },
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Retail Procurement API",
    "DESCRIPTION": "Backend-сервис автоматизации закупок (Django + DRF).",
    "VERSION": "0.1.0",
}

# -----------------------------------------------------------------------------
# Password reset
# -----------------------------------------------------------------------------
PASSWORD_RESET_TOKEN_EXPIRY_TIME = 24  # hours

# -----------------------------------------------------------------------------
# Email (console backend)
# -----------------------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "no-reply@retail.local")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@retail.local")

# -----------------------------------------------------------------------------
# Celery
# -----------------------------------------------------------------------------
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1")
CELERY_TASK_ALWAYS_EAGER = os.getenv("CELERY_TASK_ALWAYS_EAGER", "0") == "1"
CELERY_TASK_EAGER_PROPAGATES = True

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

# -----------------------------------------------------------------------------
# JWT
# -----------------------------------------------------------------------------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=2),  # 48 hours
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": False,
}

# -----------------------------------------------------------------------------
# Social Auth (social-auth-app-django)
# -----------------------------------------------------------------------------
LOGIN_REDIRECT_URL = os.getenv("LOGIN_REDIRECT_URL", "/api/docs/")
LOGIN_ERROR_URL = os.getenv("LOGIN_ERROR_URL", "/api/docs/")

AUTHENTICATION_BACKENDS = (
    "social_core.backends.google.GoogleOAuth2",
    "social_core.backends.github.GithubOAuth2",
    "django.contrib.auth.backends.ModelBackend",
)

SOCIAL_AUTH_GITHUB_KEY = os.getenv("SOCIAL_AUTH_GITHUB_KEY", "")
SOCIAL_AUTH_GITHUB_SECRET = os.getenv("SOCIAL_AUTH_GITHUB_SECRET", "")

SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.getenv("SOCIAL_AUTH_GOOGLE_OAUTH2_KEY", "")
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.getenv("SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET", "")

SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = ["openid", "email", "profile"]
SOCIAL_AUTH_CREATE_USERS = True

# -----------------------------------------------------------------------------
# Sessions (critical for OAuth "state")
# -----------------------------------------------------------------------------
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

SOCIAL_AUTH_REDIRECT_IS_HTTPS = os.getenv("SOCIAL_AUTH_REDIRECT_IS_HTTPS", "0") == "1"

# -----------------------------------------------------------------------------
# Baton config
# -----------------------------------------------------------------------------
BATON = {
    "SITE_HEADER": "Retail Procurement Admin",
    "SITE_TITLE": "Retail Procurement",
    "COPYRIGHT": "© Retail Procurement",
    "POWERED_BY": "Django + DRF + Celery",
    "CONFIRM_UNSAVED_CHANGES": True,
    "SHOW_MULTIPART_UPLOADING": True,
    "ENABLE_IMAGES_PREVIEW": True,
    "CHANGELIST_FILTERS_IN_MODAL": True,
    "CHANGEFORM_FIXED_SUBMIT_ROW": True,
}

# -----------------------------------------------------------------------------
# Sentry (Stage 9.4)
# -----------------------------------------------------------------------------
SENTRY_DSN = os.getenv("SENTRY_DSN", "").strip()
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        environment=os.getenv("SENTRY_ENVIRONMENT", "local"),
        release=os.getenv("SENTRY_RELEASE", "") or None,
        send_default_pii=os.getenv("SENTRY_SEND_PII", "0") == "1",
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.0")),
    )

# -----------------------------------------------------------------------------
# Silk settings (Stage 9.7)
# -----------------------------------------------------------------------------
if SILK_ENABLED:
    # Доступ к интерфейсу Silk — только суперюзеру
    SILKY_AUTHENTICATION = True
    SILKY_AUTHORISATION = True
    SILKY_PERMISSIONS = lambda user: bool(getattr(user, "is_superuser", False))

    # Лимиты безопасности
    SILKY_MAX_REQUEST_BODY_SIZE = 1024
    SILKY_MAX_RESPONSE_BODY_SIZE = 1024
    SILKY_MAX_RECORDED_REQUESTS = 10_000
    SILKY_MAX_RECORDED_REQUESTS_CHECK_PERCENT = 10

    # Sampling
    SILKY_INTERCEPT_PERCENT = int(os.getenv("SILKY_INTERCEPT_PERCENT", "100"))

    # Чтобы не засорять Silk: игнорим админку/батон/сам silk/доки
    SILKY_IGNORE_PATHS = [
        r"^/admin/.*",
        r"^/baton/.*",
        r"^/silk/.*",
        r"^/api/schema/.*",
        r"^/api/docs/.*",
        r"^/api/redoc/.*",
    ]

    # Python profiler (опционально)
    SILKY_PYTHON_PROFILER = os.getenv("SILKY_PYTHON_PROFILER", "0") == "1"
    SILKY_PYTHON_PROFILER_EXTENDED_FILE_NAME = True
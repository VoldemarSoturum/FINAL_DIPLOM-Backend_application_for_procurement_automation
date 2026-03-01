# config/settings_test_pg.py
from .settings import *  # noqa

import os
from datetime import timedelta

# IMPORTANT: тесты на PostgreSQL
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "procurement_db"),
        "USER": os.getenv("POSTGRES_USER", "procurement_user"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
        "HOST": os.getenv("POSTGRES_HOST", "127.0.0.1"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
        # Django будет создавать/удалять эту БД для тестов
        "TEST": {"NAME": os.getenv("TEST_POSTGRES_DB", "test_procurement_db")},
    }
}

# Emails: в памяти, проверяем через django.core.mail.outbox
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
DEFAULT_FROM_EMAIL = "no-reply@test.local"
ADMIN_EMAIL = "admin@test.local"

# чтобы не было warning по ключу
SECRET_KEY = "x" * 64

# ускоряем пароли
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# JWT пусть будет как в основном проекте
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=2),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": False,
}
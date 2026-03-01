# config/settings_test.py
from .settings import *  # noqa

# Быстрые тесты без Postgres
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Быстрее хэширование паролей
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Письма в памяти -> доступно через django.core.mail.outbox
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

DEFAULT_FROM_EMAIL = "no-reply@test.local"
ADMIN_EMAIL = "admin@test.local"
# warning про короткий SECRET_KEY в тестах
SECRET_KEY = "x" * 64
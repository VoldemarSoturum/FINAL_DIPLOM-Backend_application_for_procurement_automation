# Stage 9.2 — DRF throttling “по‑настоящему” (лимиты + предсказуемый тест)

Цель этапа: включить базовый rate‑limit на уровне Django REST Framework (DRF), **и закрепить это тестом**, который **стабильно** проходит и локально, и в Docker.

---

## 1) Что включено в проекте

В `config/settings.py` включены throttle‑классы DRF:

- `AnonRateThrottle` — лимит для неавторизованных
- `UserRateThrottle` — лимит для авторизованных

Пример (как у тебя сейчас):

```python
REST_FRAMEWORK = {
    ...
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": os.getenv("DRF_THROTTLE_ANON", "1000/min"),
        "user": os.getenv("DRF_THROTTLE_USER", "1000/min"),
    },
}
```

> Важно: throttling использует `django.core.cache` для хранения счётчиков.
> Поэтому для “боевого” окружения кэш должен быть Redis (или другой общий кеш),
> а в тестах — детерминированный backend (например, `LocMemCache`) и `cache.clear()`.

---

## 2) Как включать/выключать лимиты

### Через `.env` / `.env.docker`

- `DRF_THROTTLE_ANON=1000/min`
- `DRF_THROTTLE_USER=1000/min`

Для “жёсткого” режима можно поставить, например:

- `DRF_THROTTLE_ANON=60/min`
- `DRF_THROTTLE_USER=300/min`

---

## 3) Почему “обычные” тесты throttling иногда флапают

Причины:

1. **DRF кеширует настройки** (`api_settings`). При `override_settings(REST_FRAMEWORK=...)`
   иногда нужно сделать `api_settings.reload()`, чтобы настройки применились.
2. Throttle использует **cache**. Если не очистить кэш (`cache.clear()`), счётчик запросов
   может “протечь” между тестами.
3. `AnonRateThrottle` строит ключ на основе IP (`REMOTE_ADDR`). Если клиент/фабрика
   подставляет разные IP — будет “не ловить” лимит.

---

## 4) Предсказуемый тест throttling (рекомендуемый)

Идея: в тесте подменяем throttle‑класс на **свой**, который:

- имеет отдельный `scope` (например, `testanon`)
- возвращает **стабильный ключ** (не зависит от IP/заголовков)

Это делает тест на 100% воспроизводимым.

### Файл: `tests/test_throttling.py`

```python
import pytest
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient
from rest_framework.settings import api_settings
from rest_framework.throttling import AnonRateThrottle


class AnonThrottleForTests(AnonRateThrottle):
    """Детерминированный throttle для тестов (НЕ зависит от IP)."""

    scope = "testanon"

    def get_cache_key(self, request, view):
        # один и тот же ключ => всегда один “счётчик”
        return "throttle:testanon:key"


@pytest.mark.django_db
@override_settings(
    REST_FRAMEWORK={
        "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
        "DEFAULT_AUTHENTICATION_CLASSES": [
            "rest_framework_simplejwt.authentication.JWTAuthentication",
            "rest_framework.authentication.BasicAuthentication",
            "rest_framework.authentication.SessionAuthentication",
        ],
        "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
        "DEFAULT_THROTTLE_CLASSES": [
            "tests.test_throttling.AnonThrottleForTests",
        ],
        "DEFAULT_THROTTLE_RATES": {
            "testanon": "2/min",
        },
    },
    # Чтобы счётчик был строго локальным для теста и не зависел от Redis/окружения
    CACHES={
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    },
)
def test_throttling_anon_rate_limit_is_predictable():
    """
    Лимит 2/min => третья попытка должна дать 429.

    Почему это стабильно:
    - `cache.clear()` сбрасывает счётчики
    - `api_settings.reload()` применяет override_settings(REST_FRAMEWORK=...)
    - throttle‑ключ стабилен (не зависит от REMOTE_ADDR)
    """
    cache.clear()
    api_settings.reload()

    c = APIClient()
    url = "/api/catalog/categories/"

    r1 = c.get(url)
    r2 = c.get(url)
    r3 = c.get(url)

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 429
```

> Примечание: класс назван **не** `Test...`, чтобы pytest не пытался собирать его как тест‑класс.

---

## 5) Быстрая ручная проверка throttling

Если поставить в `.env`:

- `DRF_THROTTLE_ANON=2/min`

то можно проверить вручную:

```bash
for i in 1 2 3; do
  echo "REQ $i"
  curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/api/catalog/categories/
done
```

Ожидаемо: `200`, `200`, `429`.

---
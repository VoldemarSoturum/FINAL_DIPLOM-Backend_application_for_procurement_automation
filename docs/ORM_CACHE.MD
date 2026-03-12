# ORM Query Cache (Stage 9.6) — Redis + django-cachalot

Этот документ фиксирует внедрение **кэширования ORM-запросов** через **Redis** и **django-cachalot**, а также команды для замеров “до/после”.

---

## Что мы сделали

- **Redis** используется как backend для `django.core.cache` (единый кэш приложения).
- **django-cachalot** автоматически кэширует результаты *SELECT ORM-запросов* (Django ORM), снижая нагрузку на БД при повторных одинаковых запросах.

---

## Зависимости

В `requirements.txt` / `requirements-freeze.txt` должны присутствовать:

- `django-redis`
- `django-cachalot`

---

## Настройки

### 1) Redis cache backend (Django `CACHES`)

В `config/settings.py`:

```python
REDIS_CACHE_URL = os.getenv("REDIS_CACHE_URL", "redis://127.0.0.1:6379/2")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_CACHE_URL,
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        "TIMEOUT": 60 * 60,  # 1 hour
    }
}
```

> Почему `/2`?  
> У нас Redis Брокер/результаты Celery уже используют `/0` и `/1`.  
> Для кэша удобно выделить **отдельную DB**.

### 2) Переключатель cachalot (вкл/выкл)

Рекомендуемый паттерн (чтобы удобно сравнивать performance):

```python
CACHALOT_ENABLED = os.getenv("CACHALOT_ENABLED", "1") == "1"
```

---

## Docker / локалка: какой `REDIS_CACHE_URL` ставить

### Локально (Django запущен на хосте)

Если использовать **локальный Redis** на `127.0.0.1:6379`:

```bash
export REDIS_CACHE_URL="redis://127.0.0.1:6379/2"
```

Если Django на хосте, а Redis в `docker-compose` и наружу проброшен на `6380:6379`:

```bash
export REDIS_CACHE_URL="redis://127.0.0.1:6380/2"
```

### Внутри Docker (Django в контейнере)

```bash
REDIS_CACHE_URL=redis://redis:6379/2
```

---

## Как чистить кэш

```bash
python manage.py shell -c "from django.core.cache import cache; cache.clear(); print('cache cleared')"
```

---

## Замер производительности (до/после)

Ниже — команды, которые мы использовали, оформленные как “официальный” benchmark.

### A) Без ORM-кэша (cachalot выключен)

```bash
export CACHALOT_ENABLED=0
python manage.py shell -c "from django.core.cache import cache; cache.clear(); print('cache cleared')"

python manage.py shell -c "
import time
from django.test import Client
c=Client()
url='/api/catalog/products/?in_stock=1'
# разогрев
c.get(url)
t0=time.perf_counter()
N=50
for _ in range(N):
    c.get(url)
dt=(time.perf_counter()-t0)/N
print('AVG seconds:', dt)
"
```

**Результат (реальные цифры):**  
- AVG seconds: **0.008997581319999882**

### B) С ORM-кэшем (cachalot включен)

```bash
export CACHALOT_ENABLED=1
python manage.py shell -c "from django.core.cache import cache; cache.clear(); print('cache cleared')"

python manage.py shell -c "
import time
from django.test import Client
c=Client()
url='/api/catalog/products/?in_stock=1'
# разогрев
c.get(url)
t0=time.perf_counter()
N=50
for _ in range(N):
    c.get(url)
dt=(time.perf_counter()-t0)/N
print('AVG seconds:', dt)
"
```

**Результат (реальные цифры):**  
- AVG seconds: **0.007560304139915388**

### Итог

- Было: **0.0089976 s**
- Стало: **0.0075603 s**
- Улучшение: **≈ 15.97% быстрее** (в среднем на 50 запросах, после “разогрева”)

---

## Автотест на cachalot (идея для Stage 9.6.4)

Цель: доказать, что **второй одинаковый ORM SELECT** выполняет меньше SQL (или вообще не делает SQL), потому что отдаётся из кэша.

Подход без зависимости от Redis (на тестах используем `LocMemCache`):

```python
import pytest
from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from django.core.cache import cache

from apps.catalog.models import Category

@pytest.mark.django_db
@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    CACHALOT_ENABLED=True,
)
def test_cachalot_caches_second_orm_select():
    cache.clear()
    Category.objects.create(name="C1")

    with CaptureQueriesContext(connection) as q1:
        list(Category.objects.all())
    assert len(q1) >= 1

    with CaptureQueriesContext(connection) as q2:
        list(Category.objects.all())

    assert len(q2) < len(q1)
```

---

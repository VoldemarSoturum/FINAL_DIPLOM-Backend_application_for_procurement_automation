# Stage 9.7 — Profiling with django-silk (SQL + Python) + Docker fixes

Этот документ описывает **этап 9.7**: подключение **django-silk** для профилирования, добавление **двух профайл‑блоков** внутри `GET /api/orders/`, запуск в Docker, проверочные запросы (JWT), очистка Silk‑логов и финальный фикс бага **Docker/DNS**.

---

## Коммиты этапа

- `d6dcd98` — **stage-9.7.1:** add django-silk deps + docker libmagic  
- `0a9d9ad` — **stage-9.7.2:** configure django-silk via env + protect UI  
- `1d31436` — **stage-9.7.3:** mount silk urls behind `SILK_ENABLED`  
- `5eb3b95` — **stage-9.7.4:** add `silk_profile` blocks for client orders endpoint  
- `a350b37` — **stage-9.7.5:** docker env for silk profiling and related toggles  
- `a9940e1` — **stage-9.7.6:** tests for silk url branch + settings branch coverage  
- `e078e66` — **stage-9.7.7:** stabilize cachalot tests across envs  

---

## Что именно сделано

### 1) django-silk включается/выключается через ENV

В `config/settings.py` добавлен тумблер:

- `SILK_ENABLED=1` → Silk **включён**
- `SILK_ENABLED=0` → Silk **выключен**

При включении:
- `INSTALLED_APPS += ["silk"]`
- `MIDDLEWARE = ["silk.middleware.SilkyMiddleware"] + MIDDLEWARE`
- включена защита UI (только superuser)
- настроены ignore‑paths, лимиты и (опционально) python profiler

> Важно: Silk любит редиректить неавторизованных на `LOGIN_URL`.  
> Если у тебя нет `/accounts/login/`, нужно явно задать `LOGIN_URL=/admin/login/`.

---

### 2) Silk URLs подключаются только при включённом тумблере

В `config/urls.py`:

- если `SILK_ENABLED=True`, добавляется:
  - `path("silk/", include("silk.urls", namespace="silk"))`

---

### 3) В `ClientOrdersAPIView.get` добавлены 2 profile‑блока

Цель: в **одном и том же request** увидеть:
1) сколько времени заняли **ORM/SQL запросы**
2) сколько времени заняла **Python‑сборка ответа** (dict/list)

Реализовано через:

- `with silk_profile(name="ClientOrdersAPIView.get: build queryset")`
- `with silk_profile(name="ClientOrdersAPIView.get: build response payload")`

Так в Silk в карточке одного запроса появятся **2 профиля**, и мы видим, где “узкое место”.

---

## Переменные окружения (ENV)

### Минимум для включения Silk

```env
SILK_ENABLED=1
SILKY_INTERCEPT_PERCENT=100
SILKY_PYTHON_PROFILER=0
LOGIN_URL=/admin/login/
```

### Рекомендованные ignore‑paths (чтобы не копить “хлам”)

```python
SILKY_IGNORE_PATHS = [
    r"^/admin/.*",
    r"^/baton/.*",
    r"^/silk/.*",          # чтобы Silk не логировал сам себя
    r"^/api/schema/.*",
    r"^/api/docs/.*",
    r"^/api/redoc/.*",
]
```

---

## Где Silk UI

Зависит от того, где запущен проект:

### Локально (host)
- Django на `8000`
- Silk UI:  
  **http://127.0.0.1:8000/silk/**

### Docker (compose)
- `web` проброшен как `8001:8000`
- Silk UI:  
  **http://127.0.0.1:8001/silk/**

---

## Доступ в Silk UI (важно!)

Если включено:

```python
SILKY_AUTHENTICATION = True
SILKY_AUTHORISATION = True
SILKY_PERMISSIONS = lambda user: user.is_superuser
```

то Silk UI откроется **только** для **superuser**.

### Как войти:
1) Открыть админку:
   - `http://127.0.0.1:8001/admin/` (docker)  
   - `http://127.0.0.1:8000/admin/` (local)
2) Залогиниться superuser
3) Открыть Silk:
   - `http://127.0.0.1:8001/silk/`

> Если тебя редиректит на `/accounts/login/` и там 404 — значит `LOGIN_URL` не переопределён.  
> Поставь `LOGIN_URL=/admin/login/` в ENV (и/или в settings).

---

## Очистка Silk (чтобы не было “хлама”)

Команда, которая у нас работает:

```bash
python manage.py silk_clear_request_log
```

Дополнительно (если установлена в нашей версии Silk):

```bash
python manage.py silk_clear_profile_log
```

---

## Проверочные запросы (JWT + профилирование /api/orders)

Ниже — стабильный сценарий, который даёт красивый результат в Silk.

### 0) Очистить Silk логи

```bash
python manage.py silk_clear_request_log
```

### 1) Получить JWT токен пользователя

`/api/auth/login/` принимает JSON `{"username": "...", "password": "..."}`.

```bash
curl -s -X POST "http://127.0.0.1:8001/api/auth/login/" \
  -H "Content-Type: application/json" \
  --data-binary @- <<'JSON'
{"username":"client1","password":"nP:>.mWVmt+6~;q"}
JSON
```

В ответе будет:

```json
{"refresh":"...","access":"..."}
```

### 2) Применить access‑токен

```bash
TOKEN="PASTE_ACCESS_TOKEN_HERE"
```

### 3) Сделать несколько запросов (чтобы было с чем сравнить)

```bash
curl -s -H "Authorization: Bearer $TOKEN" "http://127.0.0.1:8001/api/orders/" > /dev/null
curl -s -H "Authorization: Bearer $TOKEN" "http://127.0.0.1:8001/api/orders/" > /dev/null
curl -s -H "Authorization: Bearer $TOKEN" "http://127.0.0.1:8001/api/orders/" > /dev/null
```

### 4) Открыть Silk UI и найти запрос

- `http://127.0.0.1:8001/silk/`
- В списке Requests выбирай **200 GET /api/orders/**
- Внутри запроса смотри:
  - количество SQL queries
  - db time
  - вкладку **Profiles** — там будут **2 блока**:
    - `ClientOrdersAPIView.get: build queryset`
    - `ClientOrdersAPIView.get: build response payload`

---

## Как читать результаты (что важно)

### Если SQL маленький, а overall большой
Значит узкое место — **Python сборка ответа**:
- большие циклы
- много вложенных items
- много преобразований типов/строк

**Типичные оптимизации:**
- пагинация
- ограничение глубины/детализации items
- сериализаторы вместо ручного dict (иногда наоборот быстрее)
- кеширование на уровне ответа (если сценарий допускает)

### Если SQL большой/много запросов
Значит узкое место — ORM/SQL:
- N+1 (не хватает prefetch/select_related)
- тяжёлые JOIN
- нет индексов
- слишком широкая выборка

---

## Docker: важные системные зависимости (libmagic)

Мы уже ловили:

```
ImportError: failed to find libmagic. Check your installation
```

Это требование `python-magic` (через `django-versatileimagefield`).

### Исправление в Dockerfile

Нужно поставить системную библиотеку:

- Debian/Ubuntu: `libmagic1` + иногда `file`

Пример:

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    make \
    libmagic1 \
    file \
  && rm -rf /var/lib/apt/lists/*
```

---

## Решение бага Docker/DNS (apt-get: Temporary failure resolving deb.debian.org)

Симптом:

```
Temporary failure resolving 'deb.debian.org'
E: Unable to locate package curl
```

Это **DNS** внутри Docker daemon.

### Фикс (Ubuntu host)

1) Создай/открой конфиг Docker daemon:

```bash
sudo mkdir -p /etc/docker
sudo nano /etc/docker/daemon.json
```

2) Вставь:

```json
{
  "dns": ["1.1.1.1", "8.8.8.8"]
}
```

3) Перезапусти Docker:

```bash
sudo systemctl restart docker
```

4) Пересобери:

```bash
docker compose down
docker compose up -d --build
```

---

## Быстрый чеклист “всё работает”

```bash
# 1) поднять стек
docker compose up -d --build

# 2) проверить, что web healthy
docker compose ps

# 3) открыть
# http://127.0.0.1:8001/admin/
# http://127.0.0.1:8001/silk/

# 4) очистить silk
docker compose exec web python manage.py silk_clear_request_log

# 5) получить token + сделать /api/orders/
# (см. секцию "Проверочные запросы")
```

---

## Примечания

- В контейнере (profile test) **Silk лучше держать выключенным** (`SILK_ENABLED=0`), чтобы не тянуть его модели и миграции.
- Если нужно тестировать ветку `urls.py` “SILK_ENABLED=True” — делай это через **stub модуль** (`sys.modules["silk.urls"] = fake`) и без реального подключения `silk` в INSTALLED_APPS.
- Для детерминизма ORM‑кэша Cachalot в тестах лучше использовать:
  - `cachalot_disabled()` для “точного выключения”
  - `LocMemCache` вместо Redis

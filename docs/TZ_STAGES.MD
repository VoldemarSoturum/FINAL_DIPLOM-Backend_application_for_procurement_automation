# Этапы выполнения ТЗ (Roadmap проекта)

Документ фиксирует, **что именно было сделано на каждом этапе**, какими артефактами это подтверждается (код/эндпоинты/тесты/докер/коммиты), и как это воспроизвести.

> Проект: **Retail Procurement API** (Django + DRF)  
> Основные домены: **Users / Catalog / Orders / Partners**  
> Асинхронщина: **Celery + Redis**  
> Документация API: **drf-spectacular (Swagger / Redoc)**

---

## Навигация по документации

> Все ссылки — **относительные пути внутри репозитория**.

- Описание API эндпоинтов проекта (APIView): `docs/API_VIEWS.md`
- Примеры запросов/ответов (curl): `docs/API_EXAMPLES.md`
- Подробно про Docker/Celery/тесты: `docs/DOCKER_AND_TESTS.md`

### Stage 9 (доп. этапы после базового ТЗ)

- 9.1 — Retry для импорта прайса: `docs/IMPORT_PRICE_RETRY.md`
- 9.2 — DRF throttling: `docs/DRF_THROTTLING.md`
- 9.3 — Social Auth (OAuth): `docs/SOCIAL_AUTH.md`
- 9.4 — Sentry: `docs/SENTRY.md`
- 9.5 — Аватары/картинки + thumbnails в Celery: `docs/IMAGES_AND_THUMBNAILS.md`
- 9.6 — ORM cache (cachalot + Redis) + бенчмарк: `docs/ORM_CACHE.md`

---

## Этап 0 — Инициализация проекта

**Цель:** развернуть базовый Django-проект, подготовить структуру приложений.

**Сделано:**
- Создан проект `config/` и приложения:
  - `apps/users`
  - `apps/catalog`
  - `apps/orders`
  - `apps/partners`
- Базовая конфигурация Django и миграции приложений.

**Артефакты:**
- `manage.py`, `config/settings.py`, `config/urls.py`
- `apps/*` + миграции

---

## Этап 1 — Базовый API слой + документация OpenAPI

**Цель:** единый REST API, Swagger/Redoc, базовая структура ответов.

**Сделано:**
- Подключён **drf-spectacular**:
  - `/api/schema/`
  - `/api/docs/` (Swagger UI)
  - `/api/redoc/` (ReDoc)
- Подключён **django-rest-passwordreset**:
  - `/api/password_reset/` (набор эндпоинтов reset)
- Добавлен **health endpoint**:
  - `GET /` → `{"status":"ok"}`  
  (чтобы корневой URL не давал 404 и можно было health-check’ить сервис)

**Артефакты:**
- `config/urls.py`
- `docs/API_VIEWS.md`
- `tests/test_health_endpoint.py`

---

## Этап 2 — Аутентификация и права доступа

**Цель:** безопасный доступ к protected endpoints, роли пользователей.

**Сделано:**
- JWT-аутентификация через **djangorestframework-simplejwt**
- Ролевые права:
  - **Client**: работает с корзиной/заказами
  - **Supplier**: работает с прайсами/заказами поставщика
- Permissions-классы вынесены в `apps/users/permissions.py`

**Артефакты:**
- `apps/users/permissions.py`
- `apps/users/views.py`, `apps/users/urls.py`, `apps/users/serializers.py`
- Тесты:
  - `tests/test_auth_smoke.py`
  - `tests/test_permissions.py`

---

## Этап 3 — Каталог (Catalog API)

**Цель:** отдавать категории/магазины/товары и поддержать фильтры.

**Сделано:**
- Публичные endpoints:
  - `GET /api/catalog/categories/`
  - `GET /api/catalog/shops/`
  - `GET /api/catalog/products/`  
    Фильтры: `category`, `shop`, `in_stock`, `q`, `ordering`
  - `GET /api/catalog/products/{id}/` (деталка + offers)
- Оптимизация запросов:
  - `select_related`, `prefetch_related`, `distinct()` для защиты от раздувания JOIN-ами.

**Артефакты:**
- `apps/catalog/views.py`, `apps/catalog/serializers.py`, `apps/catalog/models.py`
- Тесты:
  - `tests/test_catalog_api.py`

---

## Этап 4 — Корзина и заказы клиента (Orders API)

**Цель:** CRUD корзины, checkout, список заказов.

**Сделано:**
- Корзина:
  - `GET /api/basket/`
  - `POST /api/basket/items/`
  - `PATCH /api/basket/items/{item_id}/`
  - `DELETE /api/basket/items/{item_id}/`
- Checkout:
  - `POST /api/basket/checkout/`
  - Валидации: наличие товара, остатки, состояние магазина (shop.state)
  - Транзакционность (atomic + select_for_update) для корректных остатков
- Заказы клиента:
  - `GET /api/orders/` (кроме basket)

**Артефакты:**
- `apps/orders/views.py`, `apps/orders/models.py`, `apps/orders/serializers.py`
- Тесты:
  - `tests/test_orders_*` (edge cases, validation, success branches, etc.)

---

## Этап 5 — Поставщики (Partners API) + импорт прайса

**Цель:** поставщик управляет магазином, импортирует прайс, видит заказы по своему магазину.

**Сделано:**
- Импорт прайса:
  - `POST /api/partner/update/` body: `{"url": ".../price.yaml"}`
  - YAML → категории/товары/офферы (ProductInfo)
  - Важные бизнес-ветки:
    - shop.state блокирует импорт
    - защита от чужого shop (привязка к supplier)
    - zero-out позиций, которые исчезли из прайса
- Управление состоянием магазина:
  - `POST /api/partner/state/` body: `{"state": true/false}`
- Привязка/создание магазина:
  - `GET /api/partner/shop/`
  - `POST /api/partner/shop/`
  - `PATCH /api/partner/shop/`
- Заказы поставщика:
  - `GET /api/partner/orders/`  
    Фильтры: `status`, `date_from`, `date_to`

**Артефакты:**
- `apps/partners/views.py`, `apps/partners/services/importer.py`, `apps/partners/serializers.py`
- Тесты:
  - `tests/test_partner_*`, `tests/test_partners_*`
  - Бэкап тестов: `dev_tests_backup/`

---

## Этап 6 — Покрытие тестами и рефакторинг структуры тестов

**Цель:** закрыть ветки/условия, стабилизировать тесты, сохранить «золотой» набор для 100% coverage.

**Сделано:**
- Добавлены/рефакторены тесты для редких веток:
  - прямые вызовы view методов, monkeypatch импортов, проверка конфликтов/валидаторов
  - фиксы вокруг автосигналов/админки/профилей
- Выделен бэкап папки с тестами:
  - `dev_tests_backup/` — набор, который давал 100% и служит резервом

**Артефакты:**
- `tests/` (актуальные)
- `dev_tests_backup/` (резерв)

---

## Этап 7 — Вынос «медленного» в Celery (асинхронность)

**Цель:** сделать тяжёлые операции асинхронными и управляемыми очередями.

### 7.1 — Подготовка Celery
- Базовая конфигурация `config/celery.py`, настройки Celery в `config/settings.py`

### 7.2 — Partner import → Celery
- `POST /api/partner/update/` возвращает `202 + task_id` (async)
- Задача импорта:
  - `apps.partners.tasks.import_price_task`

### 7.3 — Emails → Celery
- Email-отправка вынесена в:
  - `apps.orders.tasks.send_order_emails_task`
- В checkout используется `transaction.on_commit(...)`:
  - **non-eager**: ставим задачу в очередь после commit
  - **eager**: синхронная отправка для тестов/локальной отладки

### 7.4 — Тесты async/eager + задачи
- Тесты, подтверждающие:
  - enqueue задачи (async)
  - eager поведение (emails в outbox)
  - retry branches (Retry / countdown)

### 7.5 — Docker stack (web+db+redis+celery+flower)
- Docker-compose окружение:
  - `db` (Postgres) → host `5433` (т.к. `5432` занят локальным PG)
  - `redis` → host `6380` (т.к. `6379` занят локальным Redis)
  - `web` → host `8001` (т.к. `8000` занят локальным Django)
  - `flower` → host `5556` (во избежание коллизий)
- Нормализован запуск Flower (через `celery flower ...`)

### 7.6 — Удобные команды (Makefile) + make в Dockerfile
- Makefile цели для хоста и для запуска внутри контейнера
- В Dockerfile установлен `make`, чтобы `docker compose run web make ...` работал

### 7.7 — Advanced Celery (idempotency + retry/backoff)
- Идемпотентность `send_order_emails_task` через cache-key `order:emails:sent:{order_id}`
- Retry/backoff:
  - eager (tests/dev): не ретраим, возвращаем `Status=False`
  - worker: `self.retry()` с экспоненциальным backoff, ограничение `<= 60s`
- `cleanup_stale_baskets_task` — периодическая чистка старых корзин

**Артефакты:**
- `apps/orders/tasks.py`, `apps/partners/tasks.py`
- `config/celery.py`, `config/settings.py`
- `docker-compose.yml`, `Dockerfile`, `.env.docker`
- `Makefile`
- Тесты:
  - `tests/test_partner_update_async_202.py`
  - `tests/test_orders_emails_async.py`
  - `tests/test_orders_emails_eager.py`
  - `tests/test_orders_tasks*.py`
  - `tests/test_partners_tasks*.py`

---

## Этап 8 — Документация (README + docs)

**Цель:** оформить проект так, чтобы новый человек мог поднять и понять систему.

**Сделано:**
- `README.MD` (RU + EN секции)
- `docs/DOCKER_AND_TESTS.md` — подробно про запуск, порты, workers, тесты
- `docs/API_VIEWS.md` — описание APIViews (что делает каждый endpoint)
- `docs/API_EXAMPLES.md` — примеры запросов/ответов

---

## Этап 9 — Улучшения (Stage 9.x)

> Stage 9 — набор практических улучшений, которые часто ожидают в коммерческих проектах: корректные ретраи, throttling, social login, мониторинг ошибок, обработка картинок и кэширование запросов.

### 9.1 — Fix retry для импорта прайса (RequestException passthrough)

**RU:**  
Ранее сетевые ошибки ловились внутри `import_price_from_url()` и превращались в `{"Status": False, ...}`, из-за чего Celery‑ретраи **не срабатывали**. Исправлено: `requests.RequestException` пробрасывается наверх, а формат/валидация YAML остаются обработанными в сервисе. Добавлен тест.

**EN:**  
Network errors were swallowed inside `import_price_from_url()` resulting in no Celery retries. Fixed by re-raising `requests.RequestException` so Celery task can `retry()`. YAML format/validation errors remain handled locally. Added tests.

**Docs:** `docs/IMPORT_PRICE_RETRY.md`

---

### 9.2 — DRF throttling «по-настоящему» (лимиты + тест)

**RU:**  
Добавлен базовый throttling (Anon/User) и **детерминированный тест**, чтобы проверка лимитов не флапала (учтён DRF cache + api_settings reload).

**EN:**  
Added DRF throttling (Anon/User) and a deterministic test (handles DRF settings caching + reload).

**Docs:** `docs/DRF_THROTTLING.md`

---

### 9.3 — Social login (OAuth) + API-first endpoints + тесты

**RU:**  
Подключён `social-auth-app-django` (GitHub + Google), добавлены env‑переменные и стабильные sessions для OAuth state, задокументированы Redirect URI. Реализован **API-first вариант**: endpoint возвращает auth_url JSON, complete возвращает JWT. Добавлены unit‑тесты через monkeypatch `load_backend`, без зависимости от реального провайдера.

**EN:**  
Integrated `social-auth-app-django` (GitHub + Google), env vars and stable sessions for OAuth state, redirect URIs documented. Implemented **API-first** endpoints: login returns auth_url JSON, complete returns JWT. Added unit tests with monkeypatch for `load_backend`, no real provider required.

**Docs:** `docs/SOCIAL_AUTH.md`

---

### 9.4 — Sentry (базовая интеграция + debug endpoint)

**RU:**  
Добавлена интеграция Sentry (Django + Celery), переменные окружения, endpoint `/api/debug/sentry/` (в DEBUG намеренно падает, чтобы проверить доставку issue).

**EN:**  
Added Sentry integration (Django + Celery), environment variables, debug endpoint `/api/debug/sentry/` (fails in DEBUG to generate an issue).

**Docs:** `docs/SENTRY.md`

---

### 9.5 — Картинки/аватары + асинхронная обработка thumbnails на Celery

**RU:**  
Добавлены поля изображений (VersatileImageField): `Product.image`, `UserProfile.avatar`. Реализованы upload endpoints:
- `PATCH /api/catalog/products/{id}/image/` (multipart)
- `PATCH /api/profile/avatar/` (multipart, JWT)

Добавлены фоновые задачи прогрева renditions (thumbnails/crops) после загрузки, подключены signals.  
Тесты доведены до **100% coverage**.

**EN:**  
Added image fields (VersatileImageField): `Product.image`, `UserProfile.avatar`. Implemented upload endpoints and background warming tasks for renditions, wired with signals. Tests added, coverage reached **100%**.

**Docs:** `docs/IMAGES_AND_THUMBNAILS.md`

---

### 9.6 — ORM cache (django-cachalot + Redis) + сравнение времени (before/after)

**RU:**  
Подключены `django-cachalot` и `django-redis`, настроен Redis cache backend. Включение/выключение кэша управляется переменной окружения `CACHALOT_ENABLED`. Добавлен тест, который подтверждает, что повторный ORM‑запрос кэшируется. В docs добавлены команды замера и реальные цифры.

**EN:**  
Added `django-cachalot` and `django-redis`, configured Redis cache backend. Toggle via `CACHALOT_ENABLED`. Added a test that verifies the second ORM query is cached. Documented benchmark commands and real before/after numbers.

**Docs:** `docs/ORM_CACHE.md`

---

## Быстрый чеклист

### Local (host)
```bash
pytest
```

### Docker stack
```bash
docker compose up -d --build
docker compose ps
```

### Тесты внутри контейнера
```bash
docker compose --profile test up --build --abort-on-container-exit --exit-code-from tests
```

---

## Примечания

- Два коммита `stage-4.4` присутствуют в истории как разные SHA с одинаковым сообщением — это нормально.
- В Stage 7 есть и локальные воркеры, и docker‑окружение: “host vs container” вынесено в Makefile таргеты.

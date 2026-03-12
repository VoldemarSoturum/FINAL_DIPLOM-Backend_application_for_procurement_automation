# Retail Procurement API (Django + DRF + Celery)

## Документация
- [`Этапы выполнения ТЗ (Roadmap проекта)`](docs/TZ_STAGES.MD)

- [`Описание API эндпоинов проекта, реализованных на DRF APIView`](docs/API_VIEWS.MD)

- [`Живые примеры запросов/ответов, которые использовались в проекте`](docs/API_EXAMPLES.MD)

- [`Описание Retry для импорта прайса (network passthrough → Celery retry)`](docs/IMPORT_PRICE_RETRY.MD)

- [`Подробная инструкция по интеграции Social OAth, social login (social-auth-app-django) + API-first endpoints `](docs/SOCIAL_AUTH.MD)

- [`Описание DRF throttling “по‑настоящему” (лимиты + предсказуемый тест)`](docs/DRF_THROTTLING.MD)

- [`Интеграция Error tracking Sentry`](docs/SENTRY.MD)

- [`Описание по внедрению картинок товаров/аватаров пользователей + асинхронная обработка (thumbnails) на Celery`](docs/IMAGES_AND_THUMBNAILS.MD)

- [`Подробный гайд по применению ORM Query Cache (Stage 9.6) — Redis + django-cachalot`](docs/DOCKER_AND_TESTS.MD)

## Documentation

- Detailed Docker/Celery/tests guide: `docs/DOCKER_AND_TESTS.md`

RU: Backend-сервис автоматизации закупок: каталог, поставщики, корзина, заказы, асинхронные операции через Celery.  
EN: Procurement backend: catalog, suppliers, basket/orders, async jobs via Celery.

---

## RU — Описание проекта

### Возможности
- **Каталог**
  - Категории, магазины (поставщики)
  - Товары и офферты (предложения поставщиков)
  - Фильтры в списке товаров: `category`, `shop`, `in_stock`, `q`, `ordering`
- **Заказы**
  - Корзина (BASKET): добавление/изменение/удаление позиций
  - Checkout: перевод корзины в заказ + списание остатков
  - Email-уведомления: **sync в eager-mode (тесты)**, **async через Celery (prod/dev)**  
- **Поставщики / partners**
  - Импорт прайса из YAML по URL: **async задача Celery**, API отдаёт `task_id`
  - Привязка магазина к поставщику, переключение `state`
  - Просмотр заказов поставщика с фильтрами `status`, `date_from`, `date_to`
- **Документация**
  - OpenAPI schema + Swagger UI + Redoc
- **Health endpoint**
  - `GET /` → `{"status": "ok"}` (удобно для проверок контейнера)

---

### Быстрый старт (Docker)

> Важно про порты (чтобы не конфликтовать с локальными сервисами):
- Postgres: **host 5433 → container 5432**
- Redis: **host 6380 → container 6379**
- Django: **host 8001 → container 8000**
- Flower: **host 5556 → container 5555**

#### 1) Запуск стека
```bash
docker compose up -d --build
docker compose ps
```

#### 2) Проверка health
```bash
curl -s http://127.0.0.1:8001/
# {"status":"ok"}
```

#### 3) Swagger / Redoc
- Swagger UI: `http://127.0.0.1:8001/api/docs/`
- Schema: `http://127.0.0.1:8001/api/schema/`
- Redoc: `http://127.0.0.1:8001/api/redoc/`

#### 4) Flower (мониторинг Celery)
- `http://127.0.0.1:5556/`

---

### Локальный запуск (venv)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt

python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

---

### Celery (очереди и воркеры)

Используются очереди:
- `default` — общие задачи
- `emails` — отправка email
- `imports` — импорт прайса

Если запускаешь воркеры **локально**, давай им **уникальные nodename**, чтобы не ловить `DuplicateNodenameWarning`:
```bash
celery -A config worker -l info -Q default -n worker.default@%h
celery -A config worker -l info -Q emails  -n worker.emails@%h
celery -A config worker -l info -Q imports -n worker.imports@%h
```

Проверки:
```bash
celery -A config status
celery -A config inspect ping
celery -A config inspect active_queues
```

---

### Тесты

#### На хосте
```bash
make test
make test-cov
```

#### “Профиль” тестов внутри compose-сети (через контейнер `web`)
1) Выполнить **внутри контейнера**:
```bash
docker compose exec web make test-docker
```

2) Запустить **одной командой с хоста**:
```bash
make test-docker-host
```

---

### Примечания по Swagger “серые схемы”
Это **нормально**: блок `Schemas` — это описание моделей данных (DTO/serializer output), а не “эндпоинты”. Интерфейс Swagger часто показывает схемы “приглушённо”.

---

## EN — Project Overview

### Features
- **Catalog**
  - Categories, supplier shops
  - Products + supplier offers
  - Product list filters: `category`, `shop`, `in_stock`, `q`, `ordering`
- **Orders**
  - Basket (BASKET): add/update/delete items
  - Checkout: basket → order + stock decrement
  - Email notifications: **sync in eager-mode (tests)**, **async via Celery (prod/dev)**
- **Partners**
  - YAML price import from URL: **Celery async task**, API returns `task_id`
  - Bind shop to supplier, toggle shop `state`
  - Supplier orders list with `status`, `date_from`, `date_to`
- **Docs**
  - OpenAPI schema + Swagger UI + Redoc
- **Health**
  - `GET /` → `{"status":"ok"}`

---

### Quick start (Docker)

Ports used to avoid collisions with local services:
- Postgres: **host 5433 → container 5432**
- Redis: **host 6380 → container 6379**
- Django: **host 8001 → container 8000**
- Flower: **host 5556 → container 5555**

Run:
```bash
docker compose up -d --build
```

Health:
```bash
curl -s http://127.0.0.1:8001/
```

Docs:
- Swagger UI: `http://127.0.0.1:8001/api/docs/`
- Redoc: `http://127.0.0.1:8001/api/redoc/`

Flower:
- `http://127.0.0.1:5556/`

---

### Tests
Host:
```bash
make test
make test-cov
```

Inside compose network:
```bash
docker compose exec web make test-docker
# or
make test-docker-host
```

---

## Project structure / Структура проекта (с описанием каждого файла)

> Формат: `path — RU / EN`

```text
.
├── apps — RU: Django приложения / EN: Django apps
│   ├── catalog — RU: каталог товаров / EN: catalog domain
│   │   ├── migrations — RU: миграции БД / EN: DB migrations
│   │   │   ├── 0001_initial.py — RU: начальная схема catalog / EN: initial catalog schema
│   │   │   ├── 0002_parameter_productparameter.py — RU: параметры товаров / EN: product parameters
│   │   │   ├── 0003_remove_productinfo_uniq_product_shop_info_and_more.py — RU: правки ограничений/уникальностей / EN: constraints tweaks
│   │   │   └── __init__.py — RU: пакет миграций / EN: migrations package
│   │   ├── admin.py — RU: админка catalog / EN: admin registrations for catalog
│   │   ├── apps.py — RU: конфиг приложения catalog / EN: app config
│   │   ├── __init__.py — RU: пакет приложения / EN: package marker
│   │   ├── models.py — RU: модели (Category/Shop/Product/ProductInfo/…) / EN: models
│   │   ├── serializers.py — RU: DRF сериализаторы каталога / EN: DRF serializers
│   │   ├── urls.py — RU: роуты catalog API / EN: catalog API routes
│   │   └── views.py — RU: API views каталога (filters, detail) / EN: catalog API views
│   ├── orders — RU: корзина/заказы / EN: basket & orders domain
│   │   ├── migrations — RU: миграции orders / EN: orders migrations
│   │   │   ├── 0001_initial.py — RU: начальная схема orders / EN: initial orders schema
│   │   │   └── __init__.py — RU: пакет миграций / EN: migrations package
│   │   ├── services — RU: сервисный слой / EN: service layer
│   │   │   └── emails.py — RU: формирование и отправка писем / EN: email compose/send helpers
│   │   ├── admin.py — RU: админка orders / EN: admin registrations for orders
│   │   ├── apps.py — RU: конфиг приложения orders / EN: app config
│   │   ├── __init__.py — RU: пакет приложения / EN: package marker
│   │   ├── models.py — RU: модели Order/OrderItem / EN: models
│   │   ├── serializers.py — RU: сериализаторы корзины/заказов / EN: basket/order serializers
│   │   ├── tasks.py — RU: Celery задачи (emails/cleanup) / EN: Celery tasks (emails/cleanup)
│   │   ├── urls.py — RU: роуты orders API / EN: orders API routes
│   │   └── views.py — RU: API корзины/checkout/список заказов / EN: basket/checkout/orders views
│   ├── partners — RU: поставщики (partner API) / EN: suppliers/partners
│   │   ├── migrations — RU: миграции partners / EN: partners migrations
│   │   │   └── __init__.py — RU: пакет миграций / EN: migrations package
│   │   ├── services — RU: сервисы partners / EN: partners services
│   │   │   └── importer.py — RU: импорт прайса YAML (логика парсинга/апсерта) / EN: YAML import logic (parse/upsert)
│   │   ├── admin.py — RU: админка partners / EN: admin registrations for partners
│   │   ├── apps.py — RU: конфиг приложения partners / EN: app config
│   │   ├── __init__.py — RU: пакет приложения / EN: package marker
│   │   ├── models.py — RU: модели partners (если есть) / EN: partners models (if any)
│   │   ├── serializers.py — RU: сериализаторы partners API / EN: partners serializers
│   │   ├── tasks.py — RU: Celery задача импорта (imports queue) / EN: Celery import task (imports queue)
│   │   ├── urls.py — RU: роуты partner API / EN: partner API routes
│   │   └── views.py — RU: partner endpoints (shop/state/orders/update) / EN: partner endpoints
│   ├── users — RU: пользователи/профиль/контакты/права / EN: users/profile/contacts/permissions
│   │   ├── migrations — RU: миграции users / EN: users migrations
│   │   │   ├── 0001_initial.py — RU: начальная схема users / EN: initial users schema
│   │   │   └── __init__.py — RU: пакет миграций / EN: migrations package
│   │   ├── admin.py — RU: кастомизация admin для User + UserProfile / EN: custom User admin + profile
│   │   ├── apps.py — RU: конфиг приложения users / EN: app config
│   │   ├── __init__.py — RU: пакет приложения / EN: package marker
│   │   ├── models.py — RU: UserProfile, Contact и т.п. / EN: user profile, contact models
│   │   ├── password_reset_signals.py — RU: сигналы reset password / EN: password reset signals
│   │   ├── permissions.py — RU: DRF permissions (IsClient/IsSupplier) / EN: DRF permissions
│   │   ├── serializers.py — RU: сериализаторы auth/users/contacts / EN: auth/users/contacts serializers
│   │   ├── signals.py — RU: автосоздание профиля и др. сигналы / EN: profile auto-create signals
│   │   ├── urls.py — RU: роуты users/auth/contacts / EN: users/auth/contacts routes
│   │   └── views.py — RU: auth/login/register/contacts endpoints / EN: auth + contacts views
│   └── __init__.py — RU: пакет apps / EN: apps package
├── config — RU: настройки проекта / EN: project configuration
│   ├── asgi.py — RU: ASGI entrypoint / EN: ASGI entrypoint
│   ├── celery.py — RU: инициализация Celery app, маршрутизация/очереди / EN: Celery app init + routing/queues
│   ├── __init__.py — RU: пакет config / EN: package marker
│   ├── settings.py — RU: основные настройки Django / EN: main Django settings
│   ├── settings_test_pg.py — RU: настройки для pytest + Postgres / EN: pytest settings (Postgres)
│   ├── settings_test.py — RU: тестовые настройки (вспом.) / EN: extra test settings
│   ├── urls.py — RU: корневые URL + health + docs / EN: root URLs + health + docs
│   └── wsgi.py — RU: WSGI entrypoint / EN: WSGI entrypoint
├── dev_tests_backup — RU: бэкап/черновики тестов / EN: backup/dev tests
├── .pytest_cache — RU: кеш pytest / EN: pytest cache
├── tests — RU: основной тестовый набор / EN: main tests
├── celerybeat-schedule — RU: файл расписания Celery Beat / EN: Celery Beat schedule file
├── .coveragerc — RU: настройки coverage / EN: coverage config
├── docker-compose.yml — RU: стек Docker (web/db/redis/celery/flower) / EN: Docker stack (web/db/redis/celery/flower)
├── Dockerfile — RU: Docker образ приложения / EN: app Docker image
├── .env — RU: локальные переменные окружения / EN: local environment variables
├── .env.docker — RU: env для Docker-compose / EN: env for docker-compose
├── .env.example — RU: пример env / EN: env example template
├── .gitignore — RU: исключения git / EN: git ignore rules
├── main.py — RU: вспомогательный/точка входа (если используется) / EN: helper entrypoint (if used)
├── Makefile — RU: удобные команды (test/cov/docker tests) / EN: shortcuts (tests/cov/docker tests)
├── manage.py — RU: Django manage / EN: Django manage script
├── pytest.ini — RU: конфиг pytest + coverage / EN: pytest + coverage config
├── requirements-dev.txt — RU: dev зависимости (pytest и т.п.) / EN: dev deps (pytest etc.)
├── requirements-freeze.txt — RU: “замороженные” версии (опционально) / EN: frozen versions (optional)
└── requirements.txt — RU: основные зависимости / EN: main deps

---

```



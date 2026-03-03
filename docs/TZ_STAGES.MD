# Этапы выполнения ТЗ (Roadmap проекта)

Документ фиксирует, **что именно было сделано на каждом этапе**, какими артефактами это подтверждается (код/эндпоинты/тесты/докер/коммиты), и как это воспроизвести.

> Проект: **Retail Procurement API** (Django + DRF)  
> Основные домены: **Users / Catalog / Orders / Partners**  
> Асинхронщина: **Celery + Redis**  
> Документация API: **drf-spectacular (Swagger / Redoc)**

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

**Коммиты (из вашего лога):**
- `stage-7.3`, `stage-7.4` — Celery + async/eager tests
- `stage-7.5.1`, `stage-7.5.2` — docker stack + health endpoint
- `stage-7.6.3` — make в Dockerfile + Makefile targets

---

## Этап 8 — Документация (README + docs)

**Цель:** оформить проект так, чтобы новый человек мог поднять и понять систему.

**Сделано:**
- `README.md` (RU + EN секции)
- `docs/DOCKER_AND_TESTS.md` — подробно про запуск, порты, workers, тесты
- `docs/API_VIEWS.md` — описание APIViews (что делает каждый endpoint)
- `docs/API_EXAMPLES.md` — примеры запросов/ответов

---

## Где смотреть примеры API

- Swagger: `/api/docs/`
- ReDoc: `/api/redoc/`
- Примеры curl + ответы: `docs/API_EXAMPLES.md`

---

## Проверка, что всё работает (быстрый чеклист)

### Local (host)
```bash
pytest
```

### Docker stack
```bash
docker compose up -d --build
docker compose ps
```

### Тесты внутри контейнера web
```bash
docker compose run --rm web bash -lc "make test-docker"
```

---

## Примечания

- Сообщения вида `ERROR django.request: Internal Server Error: /api/basket/checkout/` в логах тестов — **нормальны**, если тест специально проверяет ветку 500/исключения (то есть ожидаемая «ошибка» как часть сценария).
- Серые схемы в Swagger UI — обычно означает, что схемы **readOnly** или используются как вложенные объекты/ответы; это нормально для некоторых моделей (например, Basket/BasketItem).



Ниже — **хронология выполнения проекта по этапам**, составленная по истории коммитов.  
Формат: **RU + EN** (коротко и по делу). Внутри каждого этапа перечислены ключевые коммиты.

---

## Stage 1 — Инициализация проекта / Project bootstrap

**RU:** Создан Django‑проект, заведены приложения, добавлены базовые зависимости (DRF, Celery, Postgres, password reset).  
**EN:** Django project created, apps initialized, base dependencies wired (DRF, Celery, Postgres, password reset).

**Коммиты:**
- `d039442` — stage-1: init django project + init apps + drf + celery + postgres + password reset

---

## Stage 2 — База данных, модели, админка / DB models & Admin

**RU:** Реализованы модели пользователей (профиль/роли/контакты), каталог (магазины/категории/товары/предложения/параметры), заказы (order/orderitem), улучшена админка и отображение роли.  
**EN:** Implemented users (profile/roles/contacts), catalog (shops/categories/products/offers/parameters), orders (order/orderitem), admin improvements and role column.

**Коммиты:**
- `cac2454` — stage-2.1: users profile roles + contacts
- `d478aab` — stage-2.2: catalog core models (shop/category/product/productinfo)
- `50ebe1c` — stage-2.3: catalog product parameters models
- `33b25f5` — stage-2.4: orders models (order/orderitem)
- `3262c70` — stage-2.5: catalog aligns for yaml import (shop.user, productinfo external_id/model)
- `a8a9282` — stage-2.6: role inline in admin + auto-create user profile
- `a3c5601` — stage-2.7: register UserProfile model in admin
- `d736afe` — stage-2.8: show user role in admin user list

---

## Stage 3 — Поставщик, импорт прайса, партнёрские эндпоинты / Supplier flow & Import

**RU:** Добавлен импорт YAML‑прайса (upsert/параметры/обнуление отсутствующих), эндпоинты поставщика: update/import, включение/выключение магазина, привязка/получение/изменение магазина, схемы Swagger, унификация ответов.  
**EN:** Added YAML price import (upsert/parameters/zero-out missing), supplier endpoints: update/import, toggle shop state, bind/get/patch shop, Swagger schemas, unified responses.

**Коммиты:**
- `de0b58e` — stage-3.1: partner update endpoint skeleton + routing
- `7b6fced` — stage-3.2: implement yaml price import (upsert + parameters + zero-out missing items)
- `7f85017` — stage-3.4: deny price import when shop is disabled
- `32916f6` — stage-3.5: partner endpoint to toggle shop state
- `23e352a` — stage-3.6: partner endpoint to create/bind shop to supplier
- `5b25748` — stage-3.7: add GET/PATCH for supplier shop (view/update bound shop)
- `e4d7d6f` — stage-3.8: partner endpoints use serializers + spectacular schemas
- `edcf6cd` — stage-3.9: unify partner API responses and swagger schema

---

## Stage 4 — Корзина, оформление заказа, выдача заказов / Basket & Checkout

**RU:** Реализована витрина каталога (read‑only API), корзина (CRUD items), checkout с проверками наличия и фиксацией цены, выдача заказов поставщику и email‑уведомления.  
**EN:** Implemented catalog read-only API, basket CRUD, checkout with stock validation and price snapshot, supplier orders list, email notifications.

**Коммиты:**
- `029d2a5` — stage-4.1: catalog read-only api (categories/shops/products)
- `bfcb7d4` — stage-4.2.1: catalog add setting in REST_FRAMEWORK
- `50e32d0` — stage-4.2: basket api (get basket, add/update/delete items)
- `4b6a47e` — stage-4.3: checkout (basket -> new) with stock checks and price snapshot
- `dc598f9` — stage-4.4: partner orders list api (supplier sees own shop items)
- `a6ec29d` — stage-4.4: partner orders list api (supplier sees own shop items) *(дубликат сообщения в истории)*
- `1256c64` — stage-4.5: email notifications on checkout (customer + admin)

---

## Stage 5 — Аутентификация, права, reset пароля, контакты / Auth, Permissions, Reset, Contacts

**RU:** Регистрация и JWT‑аутентификация, password reset через сигнал, права для client/supplier, API контактов, выдача заказов клиента.  
**EN:** Registration and JWT auth, password reset via signal, role-based permissions, contacts CRUD API, client orders list.

**Коммиты:**
- `0ca6f5a` — stage-5.1: auth register api (client) + routing
- `297deb0` — stage-5.2: add jwt auth (simplejwt) login and refresh endpoints
- `21cff17` — stage-5.3: password reset email via django-rest-passwordreset signal
- `c469162` — stage-5.4.1: client orders api (list own orders)
- `1f1f648` — stage-5.4.2: role-based permissions (client/supplier) for api endpoints
- `dd39c3c` — stage-5.4.3: client contacts api (crud)

---

## Stage 6 — Тесты и 100% покрытие / Tests & 100% coverage

**RU:** Построен набор тестов, закрыты ветки/исключения/краевые случаи; достигнуто 100% покрытие, затем рефактор и выделение dev_tests_backup.  
**EN:** Built full test suite covering edge cases and branches; reached 100% coverage; later refactored and moved draft/backup tests to dev_tests_backup.

**Коммиты:**
- `030170c` — stage-6.1: unify orders api responses (Status/data/errors)
- `70c6a37` — stage-6.2: add postgres-based test setup, logging, progress bar and coverage
- `01fa097` — stage-6.2: postgres test setup, coverage, and expanded partner importer tests
- `919ef50` — stage-6.4: add catalog api tests (filters/search/ordering/detail)
- `efedb66` — stage-6.5: add basket/checkout edge case tests
- `04abbc2` — stage-6.6: cover email service and password reset signal branches
- `1a5ebf1` — stage-6.7: cover register invalid and contacts api (crud + not found)
- `504499c` — stage-6.8: cover partner views edge cases and filters
- `7af7d39` — stage-6.9: cover validation branches and helper/signal paths
- `b9340ab` — stage-6.10: cover more partner view branches (validation, bind, conflicts, orders)
- `abf98c4` — stage-6.11: cover model string representations
- `ff9cc65` — stage-6.12: cover remaining checkout branches in orders views
- `8ca24a9` — stage-6.13: cover remaining model/user/order view branches
- `2fc8bfc` — stage-6.14: cover importer error branches (http fail, bad yaml)
- `da5036c` — stage-6.15: cover remaining model/order/importer branches to raise coverage
- `dd195ea` — stage-6.16: add full test suite and reach 100% coverage
- `fabc6a1` — stage-6.17a: cleanup duplicate draft tests
- `53a88e0` — stage-6.17b: refactor tests + add dev_tests_backup (keep 100% coverage)

---

## Stage 7 — Celery, асинхронность, Docker, advanced tasks / Celery + Docker + Advanced

**RU:** Перенос “медленных” операций в Celery: импорт прайса и email‑отправка (eager vs async), совместимость тестов, Docker‑стек (web+db+redis+celery+flower), health endpoint, Makefile‑таргеты, advanced‑ретраи/backoff/idempotency и тестирование веток retry.  
**EN:** Moved slow operations to Celery: imports and emails (eager vs async), kept test monkeypatch compatibility, introduced Docker stack (web+db+redis+celery+flower), health endpoint, Makefile targets, advanced retry/backoff/idempotency with tests for retry branches.

**Коммиты:**
- `d862d47` — stage-7.1.1: add redis client for celery broker
- `40e0543` — stage-7.1.2: configure celery app (autodiscover)
- `f1438fb` — stage-7.1.3: add celery settings (eager in tests)
- `76d4e54` — stage-7.2.1: add celery task to send order emails
- `26a728f` — stage-7.2.2: move checkout emails to celery task (on_commit)
- `41ef29d` — stage-7.3.1: add celery task for partner price import
- `e6a1c7c` — stage-7.3.2: move partner import to celery (eager sync, async 202)
- `10a0bae` — stage-7.3.3: keep test monkeypatch compatibility + eager sync paths
- `5c0ea22` — stage-7.3: move slow operations to Celery + update partner/order views
- `317e3a5` — stage-7.4: add Celery async/eager + tasks tests and close remaining branches
- `f937ea9` — stage-7.5.1: docker-ready settings + celery config + health endpoint
- `30f9573` — stage-7.5.2: add docker-compose stack (web+db+redis+celery+flower) + docker env
- `e603c40` — stage-7.6.1: fix catalog/partner tests + tweak compose/pytest config
- `93df234` — stage-7.6.2: add Makefile targets + health endpoint test
- `7d4e0d2` — stage-7.6.3: add make to Dockerfile + split Makefile docker test targets (host vs container)
- `b12951e` — stage-7.6.4: fix docker test targets (host vs container) + align compose ports/services
- `cb64b93` — stage-7.6.5: align docker-compose ports/services to avoid host collisions
- `b623077` — stage-7.7.1: celery advanced tasks (idempotency/retry/backoff) + config/env updates
- `21f9d02` — stage-7.7.2: add tests for celery retry branches + cleanup baskets task + tasks coverage

---

## Stage 8 — Документация / Documentation

**RU:** Подготовка README (RU+EN), отдельная документация по Docker/Tests, API Views и примеры API.  
**EN:** Documentation pass: README (RU+EN), separate docs for Docker/Tests, API views, and API examples.

**(Коммиты Stage 8 будут добавлены после фиксации документации.)**

---

## Примечания / Notes

- Два коммита `stage-4.4` присутствуют в истории как разные SHA с одинаковым сообщением — это нормально, просто отражено в списке.
- В Stage 7 есть и локальные воркеры, и docker‑окружение: “host vs container” вынесено в Makefile таргеты.
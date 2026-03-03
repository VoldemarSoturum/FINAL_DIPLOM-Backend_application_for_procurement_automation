# API Examples (Requests & Responses)

Ниже — живые примеры запросов/ответов, которые использовались в проекте (curl + типовые JSON-ответы).
Формат большинства ответов **unified**:

```json
{"Status": true|false, "data": {...}|null, "errors": {...}|null}
```

## Базовые URL

- Локально на хосте (если запускаешь `python manage.py runserver`): `http://127.0.0.1:8000`
- В Docker (если у тебя проброс `8001:8000`): `http://127.0.0.1:8001`

Дальше в примерах будем писать как `BASE_URL`.

---

## 0) Health-check

### Request
```bash
curl -s http://127.0.0.1:8000/ | jq
```

### Response
```json
{"status":"ok"}
```

---

## 1) Auth (JWT)

> Точные урлы зависят от `apps.users.urls`. В наших тестах использовались:
> - `POST /api/auth/register/`
> - `POST /api/auth/login/`

### 1.1 Регистрация

#### Request
```bash
curl -s -X POST http://127.0.0.1:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"username":"supplier1","password":"StrongPass123","email":"supplier1@example.com"}' | jq
```

#### Response (пример)
```json
{
  "Status": true,
  "data": {"id": 4, "username": "supplier1", "email": "supplier1@example.com"},
  "errors": null
}
```

### 1.2 Логин (получение JWT)

#### Request
```bash
curl -s -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"supplier1","password":"StrongPass123"}' | jq
```

#### Response (пример)
```json
{
  "refresh": "eyJhbGciOi...",
  "access": "eyJhbGciOi..."
}
```

### 1.3 Использование JWT

```bash
TOKEN="eyJhbGciOi..."  # access token
curl -s http://127.0.0.1:8000/api/partner/orders/ \
  -H "Authorization: Bearer $TOKEN" | jq
```

#### Ошибка (токен невалиден/протух)
```json
{
  "detail": "Given token not valid for any token type",
  "code": "token_not_valid",
  "messages": [
    {"token_class": "AccessToken", "token_type": "access", "message": "Token is invalid"}
  ]
}
```

---

## 2) Password reset

Эндпоинты идут из `django-rest-passwordreset` и подключены как:

- `api/password_reset/ ...`

### 2.1 Запрос токена сброса

#### Request
```bash
curl -s -X POST http://127.0.0.1:8000/api/password_reset/ \
  -H "Content-Type: application/json" \
  -d '{"email":"supplier1@example.com"}' | jq
```

#### Response (пример)
```json
{"status":"OK"}
```

> Токен обычно уходит по email (в dev может печататься в консоль/лог).

### 2.2 Подтверждение сброса (пример)

> В зависимости от версии пакета путь может быть `confirm/` или похожий.
> У тебя в проекте это обычно:
> `POST /api/password_reset/confirm/`

```bash
curl -s -X POST http://127.0.0.1:8000/api/password_reset/confirm/ \
  -H "Content-Type: application/json" \
  -d '{"token":"<RESET_TOKEN>","password":"NewPass123"}' | jq
```

---

## 3) Catalog

### 3.1 Категории

#### Request
```bash
curl -s http://127.0.0.1:8000/api/catalog/categories/ | jq
```

#### Response (пример)
```json
[
  {"id": 1, "name": "Phones"},
  {"id": 2, "name": "TV"}
]
```

### 3.2 Магазины

#### Request
```bash
curl -s http://127.0.0.1:8000/api/catalog/shops/ | jq
```

#### Response (пример)
```json
[
  {"id": 1, "name": "ShopA", "url": "https://a.test", "state": true},
  {"id": 2, "name": "ShopB", "url": "https://b.test", "state": true}
]
```

### 3.3 Список товаров + фильтры

#### 3.3.1 Фильтр по категории
```bash
curl -s "http://127.0.0.1:8000/api/catalog/products/?category=1" | jq
```

#### 3.3.2 Фильтр по магазину
```bash
curl -s "http://127.0.0.1:8000/api/catalog/products/?shop=2" | jq
```

#### 3.3.3 Только товары “в наличии” (есть хотя бы один offer qty>0)
```bash
curl -s "http://127.0.0.1:8000/api/catalog/products/?in_stock=1" | jq
```

#### 3.3.4 Поиск (по name / offer name / model)
```bash
curl -s "http://127.0.0.1:8000/api/catalog/products/?q=A1" | jq
```

#### 3.3.5 Сортировка
```bash
# name ASC (по умолчанию)
curl -s "http://127.0.0.1:8000/api/catalog/products/?ordering=name" | jq

# name DESC
curl -s "http://127.0.0.1:8000/api/catalog/products/?ordering=-name" | jq
```

### 3.4 Деталка товара

#### Request
```bash
curl -s "http://127.0.0.1:8000/api/catalog/products/1/" | jq
```

#### Response (пример)
```json
{
  "id": 1,
  "name": "iPhone 15",
  "category": {"id": 1, "name": "Phones"},
  "offers": [
    {
      "id": 10,
      "external_id": 1001,
      "model": "A1",
      "name": "iPhone offer A",
      "quantity": 10,
      "price": "100.00",
      "price_rrc": "120.00",
      "shop": {"id": 1, "name": "ShopA", "url": "https://a.test", "state": true},
      "parameters": [{"parameter": "color", "value": "black"}]
    }
  ]
}
```

---

## 4) Contacts (пример CRUD)

> Урлы идут из `apps.users.urls` (в тестах использовались `/api/contacts/`).

### 4.1 Создать контакт

```bash
TOKEN="eyJhbGciOi..."

curl -s -X POST http://127.0.0.1:8000/api/contacts/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Ivan","phone":"+49-111-222","email":"ivan@example.com"}' | jq
```

### Response (пример)
```json
{"Status": true, "data": {"id": 1, "name": "Ivan", "phone": "+49-111-222", "email": "ivan@example.com"}, "errors": null}
```

### 4.2 Получить список
```bash
curl -s http://127.0.0.1:8000/api/contacts/ -H "Authorization: Bearer $TOKEN" | jq
```

### 4.3 Обновить (PATCH)
```bash
curl -s -X PATCH http://127.0.0.1:8000/api/contacts/1/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"phone":"+49-999-888"}' | jq
```

### 4.4 Удалить (DELETE)
```bash
curl -s -X DELETE http://127.0.0.1:8000/api/contacts/1/ \
  -H "Authorization: Bearer $TOKEN" | jq
```

---

## 5) Basket + Orders

### 5.1 Получить корзину (GET /api/basket/)
```bash
TOKEN="eyJhbGciOi..."

curl -s http://127.0.0.1:8000/api/basket/ \
  -H "Authorization: Bearer $TOKEN" | jq
```

### Response (пример)
```json
{
  "Status": true,
  "data": {"basket": {"id": 12, "status": "basket", "dt": "2026-03-02T22:10:00Z", "items": []}},
  "errors": null
}
```

### 5.2 Добавить позицию в корзину (POST /api/basket/items/)
```bash
curl -s -X POST http://127.0.0.1:8000/api/basket/items/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"product_info_id": 10, "quantity": 2}' | jq
```

### Ошибки (примеры)
- ProductInfo не найден:
```json
{"Status": false, "data": null, "errors": "ProductInfo not found"}
```
- Магазин выключен:
```json
{"Status": false, "data": null, "errors": "Shop is disabled"}
```
- Нет в наличии:
```json
{"Status": false, "data": null, "errors": "Out of stock"}
```

### 5.3 Обновить quantity позиции (PATCH /api/basket/items/{id}/)
```bash
curl -s -X PATCH http://127.0.0.1:8000/api/basket/items/33/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"quantity": 5}' | jq
```

### 5.4 Удалить позицию (DELETE /api/basket/items/{id}/)
```bash
curl -s -X DELETE http://127.0.0.1:8000/api/basket/items/33/ \
  -H "Authorization: Bearer $TOKEN" | jq
```

### 5.5 Checkout (POST /api/basket/checkout/)

```bash
curl -s -X POST http://127.0.0.1:8000/api/basket/checkout/ \
  -H "Authorization: Bearer $TOKEN" | jq
```

### Response (пример)
```json
{
  "Status": true,
  "data": {"order": {"id": 12, "status": "new", "dt": "2026-03-02T22:12:00Z", "items": []}},
  "errors": null
}
```

> Важно: email-уведомления отправляются:
> - **eager/tests**: синхронно (чтобы тесты видели результат)
> - **prod/worker**: через Celery (on_commit enqueue)

### 5.6 Список заказов клиента (GET /api/orders/)
```bash
curl -s http://127.0.0.1:8000/api/orders/ \
  -H "Authorization: Bearer $TOKEN" | jq
```

---

## 6) Partner (Supplier)

> Все /api/partner/* требуют supplier-role.

### 6.1 Partner update (POST /api/partner/update/) — Celery async

```bash
TOKEN="eyJhbGciOi..."

curl -s -X POST http://127.0.0.1:8000/api/partner/update/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url":"http://example.test/price.yaml"}' | jq
```

### Response (пример)
```json
{"Status": true, "data": {"task_id": "bc16e0ee-59ec-467b-82af-3d83a4273a57"}, "errors": null}
```

### 6.2 Partner state (POST /api/partner/state/)
```bash
curl -s -X POST http://127.0.0.1:8000/api/partner/state/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"state": false}' | jq
```

### Response (пример)
```json
{"Status": true, "data": {"shop": "Связной", "state": false}, "errors": null}
```

### 6.3 Partner shop (GET /api/partner/shop/)
```bash
curl -s http://127.0.0.1:8000/api/partner/shop/ \
  -H "Authorization: Bearer $TOKEN" | jq
```

### 6.4 Partner shop bind/create (POST /api/partner/shop/)
```bash
curl -s -X POST http://127.0.0.1:8000/api/partner/shop/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Supplier1 Shop","url":"https://supplier1.example"}' | jq
```

### 6.5 Partner shop patch (PATCH /api/partner/shop/)
```bash
curl -s -X PATCH http://127.0.0.1:8000/api/partner/shop/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://new-url.example"}' | jq
```

### 6.6 Partner orders (GET /api/partner/orders/)

```bash
curl -s "http://127.0.0.1:8000/api/partner/orders/?status=new&date_from=2026-01-15&date_to=2026-01-15" \
  -H "Authorization: Bearer $TOKEN" | jq
```

### Response (пример)
```json
{
  "Status": true,
  "data": {
    "orders": [
      {
        "id": 1,
        "dt": "2026-01-15T12:00:00+00:00",
        "status": "new",
        "customer": {"id": 5, "username": "client1", "email": "client1@mail.com"},
        "items": [
          {"id": 10, "product_id": 7, "product_name": "P1", "quantity": 1, "unit_price": "10.00", "unit_price_rrc": "12.00", "total": "10.00"},
          {"id": 11, "product_id": 8, "product_name": "P2", "quantity": 2, "unit_price": "5.00", "unit_price_rrc": null, "total": "10.00"}
        ]
      }
    ]
  },
  "errors": null
}
```

---

## 7) Где смотреть интерактивную документацию

- Swagger UI: `GET /api/docs/`
- Schema JSON: `GET /api/schema/`
- Redoc: `GET /api/redoc/`

---

## 8) Быстрые подсказки по debug

- Проверить, что сервис жив: `GET /`
- Проверить, что swagger поднялся: `GET /api/docs/`
- Проверить, что токен валидный: получить новый через `/api/auth/login/`
- Если задача Celery не приходит:
  - проверить `CELERY_BROKER_URL` (host vs docker)
  - проверить worker очереди `celery -A config inspect active_queues`
  - запустить воркер с уникальным именем `-n worker.imports@%h`


# API Views (DRF) — documentation

> This document explains the project’s API endpoints implemented as DRF `APIView` / generic views (Catalog) and how they behave in practice (permissions, payloads, status codes, Celery side-effects).
>
> Документ описывает API эндпоинты проекта, реализованные на DRF `APIView` / generic views (Catalog), а также их поведение (права доступа, payload, коды ответов, побочные эффекты Celery).

---

## Contents / Содержание

- [Base URLs](#base-urls)
- [Health](#health)
- [Auth & Users](#auth--users)
- [Password reset](#password-reset)
- [Catalog API](#catalog-api)
- [Orders API (Client)](#orders-api-client)
- [Partner API (Supplier)](#partner-api-supplier)
- [Common response format](#common-response-format)
- [Errors & status codes](#errors--status-codes)
- [Celery behavior](#celery-behavior)

---

## Base URLs

- **Admin:** `/admin/`
- **Swagger UI:** `/api/docs/`
- **OpenAPI schema:** `/api/schema/`
- **ReDoc:** `/api/redoc/`
- **API root:** `/api/`

---

## Health

### `GET /`
**RU:** Быстрая проверка работоспособности сервиса.  
**EN:** Lightweight service health probe.

**Response 200**
```json
{"status":"ok"}
```

---

## Auth & Users

> Exact routes are defined in `apps/users/urls.py`. Below are the routes that are used in tests and typically exposed by the project.

### `POST /api/auth/register/`
**RU:** Регистрация пользователя.  
**EN:** User registration.

**Request**
```json
{"username":"user1","password":"secret","email":"user1@example.com"}
```

**Response 201/200 (пример)**
```json
{"Status":true,"data":{"id":123,"username":"user1"},"errors":null}
```

### `POST /api/auth/login/`
**RU:** Получение JWT токенов.  
**EN:** Obtain JWT tokens.

**Request**
```json
{"username":"user1","password":"secret"}
```

**Response 200 (пример)**
```json
{"access":"<JWT_ACCESS>","refresh":"<JWT_REFRESH>"}
```

### Authorization header
For protected endpoints:
```
Authorization: Bearer <JWT_ACCESS>
```

### Contacts (examples used in tests)
> Routes are defined in `apps/users/urls.py` and implemented in `apps/users/views.py`.

- `GET /api/contacts/`
- `POST /api/contacts/`
- `GET /api/contacts/{id}/`
- `PATCH /api/contacts/{id}/`
- `DELETE /api/contacts/{id}/`

---

## Password reset

Provided by `django-rest-passwordreset`.

### `POST /api/password_reset/`
**RU:** Запрос токена сброса пароля.  
**EN:** Request password reset token.

**Request**
```json
{"email":"user1@example.com"}
```

### `POST /api/password_reset/confirm/`
**RU:** Подтверждение сброса пароля по токену.  
**EN:** Confirm password reset with token.

**Request**
```json
{"token":"<TOKEN>","password":"new_secret"}
```

---

## Catalog API

Implemented in `apps/catalog/views.py` (generic views with optimized queryset).

### `GET /api/catalog/categories/`
Public list of categories.

### `GET /api/catalog/shops/`
Public list of shops.

### `GET /api/catalog/products/`
Public list of products with filters.

**Query params**
- `category=<int>` — filter by category id
- `shop=<int>` — products that have offers in a given shop
- `in_stock=1` — only products with any offer `quantity > 0`
- `q=<str>` — search by product name / offer name / offer model (case-insensitive)
- `ordering=name` or `ordering=-name`

**Response 200 (пример)**
```json
[
  {
    "id": 10,
    "name": "iPhone 15",
    "category": {"id": 1, "name": "Phones"},
    "offers": [
      {
        "id": 100,
        "external_id": 1001,
        "model": "A1",
        "name": "iPhone offer A",
        "quantity": 10,
        "price": "100.00",
        "price_rrc": "120.00",
        "shop": {"id": 2, "name": "ShopA", "url": "https://a.test", "state": true},
        "parameters": [{"parameter": "color", "value": "black"}]
      }
    ]
  }
]
```

### `GET /api/catalog/products/{product_id}/`
Product details (same structure as list item but for a single product).

---

## Orders API (Client)

Implemented in `apps/orders/views.py` (APIView).  
Protected by: `IsAuthenticated` + `IsClient`.

### `GET /api/basket/`
**RU:** Получить текущую корзину (создаётся автоматически).  
**EN:** Get current basket (auto-created).

**Response 200**
```json
{"Status":true,"data":{"basket":{...}},"errors":null}
```

### `POST /api/basket/items/`
Add item to basket.

**Request**
```json
{"product_info_id":123,"quantity":2}
```

**Possible responses**
- `200` — item added / quantity updated
- `404` — `ProductInfo not found`
- `409` — disabled shop / out of stock
- `400` — validation errors

### `PATCH /api/basket/items/{item_id}/`
Update quantity.

**Request**
```json
{"quantity":3}
```

### `DELETE /api/basket/items/{item_id}/`
Remove item from basket.

### `POST /api/basket/checkout/`
Checkout basket (basket -> order status `new`).

**Logic (high-level)**
- Locks basket and product offers (select_for_update)
- Validates stock and shop state
- Writes final prices into `OrderItem.unit_price/unit_price_rrc`
- Decrements stock in `ProductInfo.quantity`
- Changes order status from `basket` to `new`

**Possible responses**
- `200` — order created
- `404` — basket not found (race / inside transaction)
- `409` — empty basket / stock conflict / shop disabled
- `500` — order not found after checkout (very rare)

**Response 200 (пример)**
```json
{"Status":true,"data":{"order":{...}},"errors":null}
```

### `GET /api/orders/`
List user orders excluding basket.

---

## Partner API (Supplier)

Implemented in `apps/partners/views.py`.  
Protected by: `IsAuthenticated` + `IsSupplier`.

### `POST /api/partner/update/`
Import price list by URL.

**Request**
```json
{"url":"https://example.com/price.yaml"}
```

**Behavior**
- Validates input with `PartnerUpdateSerializer`
- Enqueues Celery task `apps.partners.tasks.import_price_task`
- Returns **202 Accepted** with `task_id`

**Response 202**
```json
{"Status":true,"data":{"task_id":"<celery-task-id>"},"errors":null}
```

> **Note:** If you want to expose “task status/result” over HTTP — that’s a separate endpoint (not required by current stage). For now you can check Flower, Celery logs, or result backend.

### `POST /api/partner/state/`
Enable/disable supplier shop (`Shop.state`).

**Request**
```json
{"state":false}
```

**Responses**
- `200` — updated
- `400` — validation error or no shop bound

### `GET /api/partner/shop/`
Get bound shop for current supplier.

- `200` — shop exists
- `404` — no shop bound

### `POST /api/partner/shop/`
Bind/create a shop for supplier.

**Request**
```json
{"name":"My Shop","url":"https://myshop.example"}
```

**Responses**
- `201` — created new shop
- `200` — bound existing free shop
- `409` — already bound / name conflict
- `400` — validation errors

### `PATCH /api/partner/shop/`
Update bound shop name and/or url.

**Request**
```json
{"name":"New Name","url":"https://new-url.example"}
```

**Responses**
- `200` — updated
- `404` — no shop bound
- `409` — name conflict (another shop already uses that name)
- `400` — validation error

### `GET /api/partner/orders/`
Supplier orders view: returns only orders that contain items from supplier’s shop.

**Query params**
- `status=<str>` — filter by order status
- `date_from=YYYY-MM-DD`
- `date_to=YYYY-MM-DD`

**Response 200 (пример)**
```json
{
  "Status": true,
  "data": {
    "orders": [
      {
        "id": 12,
        "dt": "2026-03-02T18:20:00+00:00",
        "status": "new",
        "customer": {"id": 5, "username": "client1", "email": "client1@mail.com"},
        "items": [
          {
            "id": 33,
            "product_id": 7,
            "product_name": "iPhone",
            "quantity": 2,
            "unit_price": "100.00",
            "unit_price_rrc": null,
            "total": "200.00"
          }
        ]
      }
    ]
  },
  "errors": null
}
```

---

## Common response format

Most project endpoints use unified envelope:
```json
{
  "Status": true,
  "data": { },
  "errors": null
}
```

On failure:
```json
{
  "Status": false,
  "data": null,
  "errors": "..." // or dict of serializer errors
}
```

---

## Errors & status codes

Common patterns:
- `200 OK` — success
- `201 Created` — new resource created
- `202 Accepted` — async task accepted/enqueued
- `400 Bad Request` — serializer validation or input errors
- `401 Unauthorized` — missing/invalid JWT
- `403 Forbidden` — permission denied (wrong role)
- `404 Not Found` — resource not found
- `409 Conflict` — business conflict (e.g. shop disabled / stock / name conflict)
- `500 Internal Server Error` — unexpected server state

---

## Celery behavior

Tasks:
- `apps.partners.tasks.import_price_task`  
  Queue: `imports` (recommended)  
  Triggered by: `POST /api/partner/update/`

- `apps.orders.tasks.send_order_emails_task`  
  Queue: `emails` (recommended)  
  Triggered by: basket checkout (after commit)

- `apps.orders.tasks.cleanup_stale_baskets_task`  
  Queue: usually `default`  
  Triggered by: Celery Beat schedule (periodic)

Queues/workers (typical split):
- `worker.imports@...` — `-Q imports`
- `worker.emails@...` — `-Q emails`
- `worker.default@...` — `-Q default`

Tip:
- When running multiple workers on the same host, always set unique node names (`-n worker.name@%h`) to avoid `DuplicateNodenameWarning`.


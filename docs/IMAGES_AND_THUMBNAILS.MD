IMAGES_AND_THUMBNAILS.md
# Stage 9.5 — Images/Avatars + async thumbnails (Celery) + 100% tests

Этот документ описывает реализацию **Stage 9.5** в проекте **Retail Procurement API**:  
загрузка **аватара пользователя** и **картинки товара**, а также **асинхронная генерация thumbnails/renditions** через Celery (VersatileImageFieldWarmer).  
В конце — проверочные запросы (curl) и заметки по тестам/покрытию.

---

## 0) Коммиты этапа

Основные коммиты:

- `67cb878` — **stage-9.5.1**: deps для изображений + MEDIA settings + раздача uploads в DEBUG  
- `76c778e` — **stage-9.5.2**: `Product.image` и `UserProfile.avatar` (versatileimagefield) + миграции  
- `756046a` — **stage-9.5.3**: upload endpoints + serializers (avatar/product image)  
- `c672704` — **stage-9.5.4**: enqueue thumbnail processing on upload + tests + fixtures

Дальше «добивка» покрытия/стабилизация тестов:

- `5e9e387` — stage-9.1.x: importer tests aligned for RequestException passthrough  
- `34fddef` — stage-9.5.x: stabilize product image upload multipart test  
- `30eaab9` — stage-9.2.x: deterministic anon throttling test  
- `990469d` — stage-9.x: harden users admin tests against AlreadyRegistered + cover import branches  
- `381f034` — stage-9.4.x: cover config urls debug media + sentry debug endpoint  
- `197f76e` — stage-9.4.x: cover settings sentry init branch  
- `e6ba9bc` — stage-9.5.x: cover profile serializer contacts/avatar branches  
- `eb4fa2b` — stage-9.5.x: cover profile avatar upload missing file branch  
- `c1fb64c` — stage-9.5.x: cover celery image warmer tasks (users/catalog)

---

## 1) Что сделано по Stage 9.5

### A) Media uploads (Django)
- Включены `MEDIA_URL` и `MEDIA_ROOT`
- Добавлена раздача `/media/…` в `DEBUG=True` (для локали и dev-режима)
- Загрузка файлов в `MEDIA_ROOT` (по умолчанию: `<project>/media/`)

### B) Поля в моделях (VersatileImageField)
- `apps/catalog/models.py`
  - `Product.image = VersatileImageField(upload_to="products/", blank=True, null=True)`
- `apps/users/models.py`
  - `UserProfile.avatar = VersatileImageField(upload_to="avatars/", blank=True, null=True)` *(путь может отличаться — ориентируйся по своему коду)*

### C) Upload endpoints (DRF)
- **Avatar upload**  
  `PATCH /api/profile/avatar/` (multipart/form-data)  
  Поле: `avatar=<file>`  
  Требует JWT (обычно `IsAuthenticated`).

- **Product image upload**  
  `PATCH /api/catalog/products/<id>/image/` (multipart/form-data)  
  Поле: `image=<file>`  
  Права можно ужесточать позже (на этом этапе допустимо `AllowAny` или `IsAuthenticated`).

### D) Async thumbnail processing (Celery)
После успешной загрузки файла:
- ставим задачу в Celery на **прогрев renditions** (warm-up)
- используем `VersatileImageFieldWarmer`, который создаёт заранее заданные размеры/кропы

---

## 2) Настройки (settings.py)

### Media
```python
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
```

### VersatileImageField
Идея: **не генерировать** thumbnails «по требованию» в момент запроса (дорого),  
а прогревать их фоном после загрузки.

```python
VERSATILEIMAGEFIELD_SETTINGS = {
    "create_on_demand": False,
}

VERSATILEIMAGEFIELD_RENDITION_KEY_SETS = {
    "avatar": [
        ("full", "url"),
        ("sm", "thumbnail__64x64"),
        ("md", "thumbnail__256x256"),
        ("sq", "crop__128x128"),
    ],
    "product": [
        ("full", "url"),
        ("sm", "thumbnail__300x300"),
        ("md", "thumbnail__600x600"),
        ("sq", "crop__400x400"),
    ],
}
```

---

## 3) Раздача /media в DEBUG (config/urls.py)

В dev-режиме можно раздавать загрузки напрямую Django:

```python
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    ...
] + (static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) if settings.DEBUG else [])

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

> !!!!! В проде так делать нельзя — нужен Nginx/Traefik/Cloud storage.

---

## 4) Celery задачи прогрева изображений

### A) Прогрев avatar

`apps/users/tasks.py`
- `warm_user_avatar_renditions(profile_id: int) -> dict`
- если профиля/аватара нет: `{"Status": False, "Error": "..."}`
- иначе прогревает `rendition_key_set="avatar"`

### B) Прогрев product image

`apps/catalog/tasks.py`
- `warm_product_image_renditions(product_id: int) -> dict`
- если товара/картинки нет: `{"Status": False, "Error": "..."}`
- иначе прогревает `rendition_key_set="product"`

---

## 5) Как именно задачи запускаются после upload

Типичный паттерн (то, что у нас реализовано в Stage 9.5.4):

1) DRF endpoint сохраняет `avatar`/`image` в модель и делает `save(update_fields=[...])`
2) дальше либо:
   - сигнал `post_save`/`pre_save` + `transaction.on_commit(...)`
   - либо прямо в APIView после save: `delay(profile.id)` / `delay(product.id)`
3) Celery worker принимает задачу и прогревает thumbnails.

Важно:
- лучше ставить задачу **через `transaction.on_commit`**, чтобы не прогревать файл, который ещё не зафиксирован.

---

## 6) Проверочные запросы (curl)

### 6.1 Получить список продуктов и выбрать id
```bash
curl -s "http://127.0.0.1:8000/api/catalog/products/?in_stock=1" | head -c 2000
```

### 6.2 Получить продукт по id
```bash
curl -i "http://127.0.0.1:8000/api/catalog/products/11/"
```

### 6.3 Загрузить картинку товара
```bash
curl -i -X PATCH \
  -F "image=@tests/fixtures/product.png" \
  "http://127.0.0.1:8000/api/catalog/products/11/image/"
```

Ожидаемо:
- `HTTP/1.1 200 OK`
- в JSON: `"image": "/media/products/<...>.png"` (или абсолютный URL — зависит от serializer context)

Проверка раздачи:
```bash
curl -I "http://127.0.0.1:8000/media/products/<FILENAME>.png"
```

---

### 6.4 Получить JWT token (если login работает)
```bash
curl -s -X POST "http://127.0.0.1:8000/api/auth/login/" \
  -H "Content-Type: application/json" \
  -d '{"username":"supplier1","password":"<PASSWORD>"}'
```

Или (если удобнее) получить access_token через shell (SimpleJWT):
```bash
python manage.py shell -c "from django.contrib.auth import get_user_model; from rest_framework_simplejwt.tokens import RefreshToken; u=get_user_model().objects.get(username='supplier1'); print(str(RefreshToken.for_user(u).access_token))"
```

### 6.5 Загрузить аватар
```bash
TOKEN="<ACCESS_TOKEN>"
curl -i -X PATCH \
  -H "Authorization: Bearer $TOKEN" \
  -F "avatar=@tests/fixtures/avatar.png" \
  "http://127.0.0.1:8000/api/profile/avatar/"
```

Ожидаемо:
- `HTTP/1.1 200 OK`
- профиль в JSON (включая `"avatar": "/media/avatars/<...>.png"`)

Проверка раздачи:
```bash
curl -I "http://127.0.0.1:8000/media/avatars/<FILENAME>.png"
```

---

## 7) Тесты и 100% покрытие

На этом этапе были стабилизированы «сложные» места:

### Multipart upload (product image)
- важно подавать **валидный PNG**, а не «псевдо байты»
- в тестах делается через base64 1x1 png или fixture-file

### Avatar upload
- отдельный тест на ветку **missing file** (`avatar` не передали) -> ожидаем 400
- отдельные тесты на ветки сериализатора профиля: контакты/аватар/фоллбеки

### Celery image warmer tasks
- тесты закрывают:
  - ветка “нет объекта/нет картинки” -> Status False
  - ветка success -> warm() called, returned dict includes created/failed

---

## 8) Частые проблемы и решения

### 8.1 `curl: (26) Failed to open/read local data`
Путь к файлу неверный.  
Правильно (если файл лежит в `tests/fixtures/`):
```bash
-F "image=@tests/fixtures/product.png"
```

### 8.2 500 NameError `get_object_or_404` is not defined
В `apps/catalog/views.py` нужно импортировать:
```python
from django.shortcuts import get_object_or_404
```
---

### Результаты покрытия тестами кода 
---
```bash
======================================================================================== tests coverage ========================================================================================
_______________________________________________________________________ coverage: platform linux, python 3.11.0-final-0 ________________________________________________________________________

Name                                   Stmts   Miss Branch BrPart  Cover   Missing
----------------------------------------------------------------------------------
apps/catalog/admin.py                     31      0      0      0   100%
apps/catalog/apps.py                       6      0      0      0   100%
apps/catalog/models.py                    64      0      0      0   100%
apps/catalog/serializers.py               37      0      2      0   100%
apps/catalog/signals.py                   10      0      2      0   100%
apps/catalog/tasks.py                     13      0      2      0   100%
apps/catalog/urls.py                       3      0      0      0   100%
apps/catalog/views.py                     60      0      8      0   100%
apps/orders/admin.py                      16      0      0      0   100%
apps/orders/apps.py                        4      0      0      0   100%
apps/orders/models.py                     35      0      0      0   100%
apps/orders/serializers.py                25      0      0      0   100%
apps/orders/services/emails.py            43      0     10      0   100%
apps/orders/tasks.py                      37      0      6      0   100%
apps/orders/urls.py                        3      0      0      0   100%
apps/orders/views.py                     137      0     40      0   100%
apps/partners/admin.py                     1      0      0      0   100%
apps/partners/apps.py                      4      0      0      0   100%
apps/partners/models.py                    1      0      0      0   100%
apps/partners/serializers.py              35      0      2      0   100%
apps/partners/services/importer.py        82      0     22      0   100%
apps/partners/tasks.py                    21      0      4      0   100%
apps/partners/urls.py                      3      0      0      0   100%
apps/partners/views.py                   144      0     58      0   100%
apps/users/admin.py                       33      0      2      0   100%
apps/users/apps.py                         7      0      0      0   100%
apps/users/models.py                      29      0      0      0   100%
apps/users/password_reset_signals.py      13      0      2      0   100%
apps/users/permissions.py                 12      0      0      0   100%
apps/users/serializers.py                 44      0      6      0   100%
apps/users/signals.py                     16      0      4      0   100%
apps/users/social_api.py                  46      0      6      0   100%
apps/users/tasks.py                       13      0      2      0   100%
apps/users/urls.py                         5      0      0      0   100%
apps/users/views.py                       61      0     12      0   100%
config/settings.py                        71      0      2      0   100%
config/urls.py                            19      0      4      0   100%
----------------------------------------------------------------------------------
TOTAL                                   1184      0    196      0   100%
Coverage HTML written to dir htmlcov
===================================================================================== 137 passed in 7.51s ======================================================================================
```
---
# Stage 9.1 — Retry для импорта прайса (network passthrough → Celery retry)

## Зачем это нужно

Раньше сетевые ошибки при скачивании YAML (`requests.get(...)`) **перехватывались внутри** `import_price_from_url()` и превращались в ответ:

```json
{"Status": false, "Error": "...", "http_status": 400}
```

Из-за этого Celery-задача `apps.partners.tasks.import_price_task` **не видела исключение** и **не могла выполнить `self.retry(...)`** при временных проблемах сети (DNS, timeout, 502 и т.п.).

**Цель Stage 9.1:**
- сетевые ошибки (`requests.RequestException`) **пробрасываем наружу** из `import_price_from_url()`
- `import_price_task()` ловит `RequestException` и делает `retry/backoff` (в worker-режиме), а в eager-режиме (тесты/dev) возвращает `Status=False`.

---

## Что изменили

### 1) `apps/partners/services/importer.py`

Ключевой момент: `requests.RequestException` **НЕ “съедаем”**.

```python
try:
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
except requests.RequestException:
    raise  # <-- важно: Celery-task поймает это и сделает retry
except Exception as e:
    return {"Status": False, "Error": f"Failed to fetch url: {e}", "http_status": 400}
```

Остальные ошибки остаются обработанными внутри importer’а и возвращают unified-ответ:
- `yaml.YAMLError` / “Invalid YAML”
- missing keys: `shop/categories/goods`
- “bad goods item”
- бизнес-валидация: disabled shop / belongs to another supplier

---

### 2) `apps/partners/tasks.py`

Там уже есть логика:

- `CELERY_TASK_ALWAYS_EAGER=True` → **не ретраим**, возвращаем `{"Status": False, ...}`
- `CELERY_TASK_ALWAYS_EAGER=False` (worker) → `countdown = min(2 ** retries, 60)` и `raise self.retry(...)`

После изменения importer’а **retry реально начинает работать**.

---

## Как проверить руками (локально)

### Вариант A — через API (асинхронно)

```bash
curl -s -X POST http://127.0.0.1:8000/api/partner/update/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url":"http://example.test/price.yaml"}'
```

Если домен не резолвится / сеть упала — задача уйдёт в очередь `imports`, а воркер покажет retry/ошибку.

---

### Вариант B — напрямую дернуть задачу из shell

```bash
python manage.py shell -c "from apps.partners.tasks import import_price_task; r=import_price_task.apply_async(kwargs={'user_id': 4, 'url':'http://example.test/price.yaml'}, queue='imports'); print(r.id)"
```

Смотри лог `worker.imports`.

---

## Тесты (обязательная часть Stage 9.1)

### 1) Unit-тест на importer: passthrough сетевого исключения

Файл: `tests/test_importer_network_retry_passthrough.py`

Смысл:
- monkeypatch `requests.get` → бросает `requests.RequestException`
- ожидаем **исключение наружу**, а не `{"Status": False, ...}`

```python
with pytest.raises(requests.RequestException):
    import_price_from_url(user=supplier_user, url="http://example.test/boom.yaml")
```

### 2) Тест на Celery retry-ветку (если делали)

Файл (пример): `tests/test_partners_tasks_retry_branches.py`

Смысл:
- `@override_settings(CELERY_TASK_ALWAYS_EAGER=False)`
- monkeypatch `import_price_from_url` → бросает `requests.RequestException`
- ожидаем `celery.exceptions.Retry` (из `self.retry(...)`)

---

## Важные замечания

### Почему именно `requests.RequestException`
- `HTTPError` (из `raise_for_status()`) — тоже `RequestException`
- timeout / connection error / DNS error — тоже `RequestException`

Это удобно: **все временные сетевые сбои → retry**.

### Что НЕ должно ретраиться
Ошибки формата/данных/валидации:
- плохой YAML
- не хватает ключей
- неверные структуры категорий/товаров
- “shop disabled”, “belongs to another supplier”

Это не временные проблемы — retry бессмысленен.

---

## Итог Stage 9.1

- importer перестал “гасить” сетевые ошибки
- Celery-ретраи начали работать по-настоящему
- добавлен тест, закрепляющий поведение (passthrough)
- при необходимости — тест на retry-ветку самой задачи
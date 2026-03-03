# Docker & Tests Guide (RU/EN)

> Этот документ — “подробная” часть документации: запуск Docker-стека, тесты (host/container), Celery воркеры/очереди, типовые проблемы с портами и их быстрое исправление.  
> README остаётся компактным и ссылается сюда.

---

## RU — Docker stack (web + db + redis + celery + flower)

### 1) Требования на хосте

- Docker + Docker Compose v2
- (Опционально) локальные сервисы Postgres/Redis/Django **могут быть запущены**, но тогда важно избегать конфликтов портов (см. ниже).

Проверка занятых портов:
```bash
sudo ss -ltnp | egrep ':(5432|5433|6379|6380|8000|8001|5555|5556)\b' || true
```

### 2) Порты и почему так

В проекте осознанно разведены порты, потому что локально у тебя уже работают сервисы:

- **Postgres**: локально `5432` занят → контейнерный Postgres публикуется как **host:5433 → container:5432**
- **Redis**: локально `6379` занят → контейнерный Redis публикуется как **host:6380 → container:6379**
- **Django web**: локально `8000` занят → контейнерный web публикуется как **host:8001 → container:8000**
- **Flower**: публикуем как **host:5556 → container:5555**

Внутри docker-сети сервисы общаются по именам контейнеров и **внутренним** портам:
- Postgres: `db:5432`
- Redis: `redis:6379`
- Django: `web:8000`

### 3) .env.docker — важные параметры для Docker

В Docker-контейнерах **POSTGRES_HOST должен быть `db`**, а для Celery/Redis — `redis`.

Смотри файл `.env.docker` в корне проекта.

### 4) Запуск Docker-стека

Старт:
```bash
docker compose up -d --build
docker compose ps
```

Логи:
```bash
docker compose logs -f web
docker compose logs -f celery_worker
docker compose logs -f celery_beat
docker compose logs -f flower
```

Остановка:
```bash
docker compose down
```

С полным удалением volume (данные БД будут потеряны):
```bash
docker compose down -v
```

### 5) Проверка, что сервисы “живы”

- Health endpoint (корень сайта):
```bash
curl -s http://127.0.0.1:8001/ && echo
# ожидаем: {"status":"ok"}
```

- Админка:
  - `http://127.0.0.1:8001/admin/`

- Swagger UI:
  - `http://127.0.0.1:8001/api/docs/`

- Flower:
  - `http://127.0.0.1:5556/`

### 6) Почему на `/` раньше был 404?

Потому что в `config/urls.py` изначально не было `path("", health)`. Сейчас добавлен health endpoint, поэтому корень возвращает JSON.

---

## RU — Tests (host vs container)

### 1) Запуск тестов на хосте (локальная БД/настройки)

Обычный запуск:
```bash
make test
```

С покрытием:
```bash
make test-cov
```

### 2) Запуск тестов “внутри compose-сети”

Есть два корректных сценария:

**A) Запуск внутри контейнера `web` (предпочтительно для CI-like окружения):**
```bash
docker compose exec web make test-docker
```

**B) Запуск с хоста, но внутри контейнера через обёртку:**
```bash
make test-docker-host
```

Почему не просто `make test-docker` на хосте?
- `test-docker` рассчитан на то, что ты уже **находишься внутри контейнера** (там нет вызовов `docker compose ...`).
- `test-docker-host` — это удобная оболочка “одной командой” с хоста.

---

## RU — Celery: очереди, воркеры, как тестировать

### 1) Очереди

Используются очереди:
- `default` — общие задачи
- `emails` — отправка писем
- `imports` — импорт прайсов

Проверить очереди:
```bash
celery -A config inspect active_queues
```

### 2) Воркеры и имена нод

Если видишь предупреждение:
`DuplicateNodenameWarning: Received multiple replies from node name: celery@ubuntu`

Это значит: запущены несколько воркеров с одинаковым `-n`.
Решение — запускать с уникальными именами:
```bash
celery -A config worker -l info -Q default -n worker.default@%h
celery -A config worker -l info -Q emails  -n worker.emails@%h
celery -A config worker -l info -Q imports -n worker.imports@%h
```

### 3) “Как проверить, что работает emails”

Самый простой тест — оформить заказ (checkout).  
Если `EMAIL_BACKEND` консольный — письма будут в логах воркера `emails` (или в `web`, если eager).

Проверка “пингом” воркеров:
```bash
celery -A config inspect ping
celery -A config status
```

### 4) “Как проверить, что работает imports”

У тебя есть два пути:

**A) Через API (нужен валидный JWT):**
1) Получи access token для пользователя-поставщика.
2) Дёрни эндпоинт:
```bash
curl -s -X POST http://127.0.0.1:8001/api/partner/update/ \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"url":"http://example.test/price.yaml"}'
```
Ожидаемый формат ответа (async):
```json
{"Status": true, "data": {"task_id": "<uuid>"}, "errors": null}
```

**B) Напрямую через Django shell (самый надёжный для диагностики):**
```bash
python manage.py shell -c "from apps.partners.tasks import import_price_task; r=import_price_task.apply_async(kwargs={'user_id': 4, 'url':'http://example.test/price.yaml'}, queue='imports'); print('task_id=', r.id)"
```

### 5) Почему `celery call ... -Q imports` не работает?

Команда `celery call` **не поддерживает** опцию `-Q`.  
Для маршрутизации в очередь используй:
- `.apply_async(queue="imports")` из Python
- или настройки routing в `config/celery.py`

---

## RU — Типовые проблемы и быстрые решения

### Проблема: “port is already in use” (5432/6379/8000/5555)

Решение:
- не публиковать конфликтный порт наружу
- или сменить host-port (как в текущем compose: 5433/6380/8001/5556)

### Проблема: Flower падает “No such option: --port”

Решение: в образе `mher/flower` entrypoint не всегда “celery flower”.
Используй явный entrypoint `["celery"]` и команду вида:
```yaml
entrypoint: ["celery"]
command: ["--broker=redis://redis:6379/0", "flower", "--address=0.0.0.0", "--port=5555"]
```

---

## EN — Quick reference (Docker + tests)

### Run stack
```bash
docker compose up -d --build
docker compose ps
```

### Health / Docs / Admin / Flower
- Health: `http://127.0.0.1:8001/`
- Admin: `http://127.0.0.1:8001/admin/`
- Swagger: `http://127.0.0.1:8001/api/docs/`
- Flower: `http://127.0.0.1:5556/`

### Run tests inside container network
```bash
docker compose exec web make test-docker
# or from host:
make test-docker-host
```

### Celery workers with explicit queues
```bash
celery -A config worker -l info -Q default -n worker.default@%h
celery -A config worker -l info -Q emails  -n worker.emails@%h
celery -A config worker -l info -Q imports -n worker.imports@%h
```

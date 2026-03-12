# Stage 9.4 — Error tracking (Sentry / Rollbar / Hawk)

Коммит: `786f835 stage-9.4: add Sentry integration + debug endpoint`

Этот этап добавляет **базовую интеграцию error-tracking** (на примере **Sentry**) и **специальный endpoint**, который намеренно падает, чтобы быстро проверить, что события действительно улетают в систему мониторинга.

> В проекте реализовано именно **Sentry** (через `sentry-sdk`).
> Rollbar/Hawk — как альтернативы (ниже есть краткая шпаргалка).

---

## 1) Что добавлено в проект

### 1.1. Sentry SDK в зависимостях
В `requirements.txt` добавлен пакет `sentry-sdk` (Django/Celery интеграции используются через него).

### 1.2. Инициализация Sentry в `config/settings.py`
Sentry инициализируется **только если задан DSN**:

- если `SENTRY_DSN` пустой → Sentry **не включается** (безопасно для dev/CI);
- если `SENTRY_DSN` задан → включаются интеграции:
  - `DjangoIntegration()` — перехват ошибок в запросах Django
  - `CeleryIntegration()` — перехват ошибок в задачах Celery

Логика (как у тебя):
- `SENTRY_DSN = os.getenv("SENTRY_DSN", "").strip()`
- `if SENTRY_DSN: sentry_sdk.init(...)`

### 1.3. Debug endpoint
Добавлен endpoint:

- `GET /api/debug/sentry/`

Поведение:
- при `DEBUG=True` → endpoint **намеренно делает `1/0`** и возвращает **500**
- при `DEBUG=False` → endpoint скрыт и возвращает **404** (`Http404`)

> Это важно, чтобы в production случайно не держать “кнопку падения”.

---

## 2) Как заполнить переменные окружения

В `.env` / `.env.docker` / `.env.example` добавлены переменные:

```env
# -----------------------
# Sentry (Stage 9.4)
# -----------------------
SENTRY_DSN=
SENTRY_ENVIRONMENT=local
SENTRY_RELEASE=
SENTRY_TRACES_SAMPLE_RATE=0.0
SENTRY_SEND_PII=0
```

### `SENTRY_DSN`
Это **DSN проекта**, который выдаёт **сам Sentry** (его не “генерируют вручную”).

Где взять:
1) Создай проект в Sentry
2) Sentry покажет DSN вида:
   `https://<public_key>@o<org_id>.ingest.sentry.io/<project_id>`
3) Скопируй в `SENTRY_DSN`

Если `SENTRY_DSN` пустой — интеграция просто не включится.

### `SENTRY_ENVIRONMENT`
Метка окружения: `local`, `docker`, `stage`, `prod`.

Примеры:
- `SENTRY_ENVIRONMENT=local` (локально)
- `SENTRY_ENVIRONMENT=docker` (в контейнерах)

### `SENTRY_RELEASE`
Версия релиза (помогает группировать ошибки). Можно указывать:
- `SENTRY_RELEASE=stage-9.4`
- или git commit/tag.

### `SENTRY_TRACES_SAMPLE_RATE`
Про performance tracing (APM).

- `0.0` — выключено (безопасно по умолчанию)
- `0.1` — 10% транзакций
- `1.0` — 100% транзакций (обычно дорого/шумно)

### `SENTRY_SEND_PII`
Отправка персональных данных (PII):

- `0` — не отправлять (рекомендуемо)
- `1` — отправлять (только если реально нужно и ты понимаешь риски)

---

## 3) Проверка, что Sentry реально работает

### 3.1. Проверка через debug endpoint
Убедись, что:
- `DEBUG=True`
- `SENTRY_DSN` заполнен

Открой:

```bash
curl -i http://127.0.0.1:8000/api/debug/sentry/
```

Ожидаемо:
- HTTP 500 (потому что там `1/0`)
- В Sentry появляется **Issue / Event**

Ты уже подтвердил, что “issues в sentry реально падает” — значит всё ок.

### 3.2. Проверка, что endpoint скрыт при DEBUG=False

```bash
# либо export DEBUG=0, либо DEBUG=0 в .env
curl -i http://127.0.0.1:8000/api/debug/sentry/
```

Ожидаемо:
- 404 Not Found

---

## 4) Проверка интеграции с Celery

Так как подключена `CeleryIntegration()`, ошибки задач тоже должны улетать.

### 4.1. Быстрый smoke-тест
Любая задача, которая бросит исключение (или упадёт из-за неверных входных данных), должна создать event в Sentry.

Пример (идея):
- вызвать задачу с некорректными аргументами
- или временно добавить тестовую задачу, которая делает `1/0` (и затем удалить)

### 4.2. Что смотреть в Sentry
- traceback
- теги `environment`, `release`
- breadcrumbs (для web-запросов)

---

## 5) Docker: как включить Sentry в контейнерах

### 5.1. Добавь переменные в `.env.docker`

```env
SENTRY_DSN=...ваш_dsn...
SENTRY_ENVIRONMENT=docker
SENTRY_RELEASE=stage-9.4
SENTRY_TRACES_SAMPLE_RATE=0.0
SENTRY_SEND_PII=0
```

### 5.2. Перезапусти контейнеры

```bash
docker compose up -d --build
```

### 5.3. Важно
Переменные должны быть доступны и в `web`, и в `celery_worker` (иначе ошибки celery не улетят).

---

## 6) Безопасность и best practices

1) **Не коммить DSN** в репозиторий (храни в `.env`/secrets).
2) Debug endpoint держать **только под DEBUG** (у тебя так и сделано).
3) В проде лучше:
   - `SENTRY_SEND_PII=0`
   - `SENTRY_TRACES_SAMPLE_RATE` <= 0.1 или 0.0

---

## 7) Troubleshooting

### 7.1. Issue не появляется
Проверь DSN:

```bash
python manage.py shell -c "from django.conf import settings; print('SENTRY_DSN=', getattr(settings,'SENTRY_DSN', None))"
```

Проверь:
- DSN не пустой и без пробелов
- есть доступ в интернет
- endpoint реально возвращает 500

### 7.2. Слишком много событий
- снизь `SENTRY_TRACES_SAMPLE_RATE`
- при необходимости добавь фильтрацию/ignore для шумных исключений

---

## 8) Альтернативы: Rollbar / Hawk (коротко)

### Rollbar
- Django: https://docs.rollbar.com/docs/django
- Celery: https://docs.rollbar.com/docs/celery

Схема похожая:
- ставишь пакет
- задаёшь токен
- подключаешь интеграцию
- делаешь test endpoint

### Hawk
- Интеграции: https://docs.hawk-tracker.ru/integrations
- Сайт: https://hawk-tracker.ru/

---

## 9) Быстрая шпаргалка

Проверить env:
```bash
python manage.py shell -c "import os; print('SENTRY_DSN=', os.getenv('SENTRY_DSN'))"
```
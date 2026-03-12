# Stage 9.3 — Social login (social-auth-app-django) + API-first endpoints

Коммиты этапа:

- `170a2e3` — **stage-9.3.2:** social auth env vars + stable sessions for OAuth state + redirect URI docs
- `c3a7d66` — **stage-9.3.4:** API-first social auth endpoints (JSON auth_url + JWT complete)
- `8ca9319` — **stage-9.3.5:** tests for api-first social auth (monkeypatch load_backend)
- `4cf7a21` — **stage-9.3.4.2:** fix API-first social tests (complete endpoint is GET-only)

> **Важно про OAuth:** стартовать нужно с `.../login/...`, а `.../complete/...` вызывается **только** провайдером (Google/GitHub) при редиректе обратно и содержит `?code=...&state=...`.

---

## 1) Что реализовано в проекте

### 1.1. Classic redirect-flow (social_django urls)
Этот режим делает редирект на провайдера и после подтверждения возвращает на `complete` URL.

Роуты (в `config/urls.py`):

- `GET /api/auth/social/login/github/`
- `GET /api/auth/social/login/google-oauth2/`
- callback от провайдера:
  - `/api/auth/social/complete/github/?code=...&state=...`
  - `/api/auth/social/complete/google-oauth2/?code=...&state=...`

> Этот вариант удобен для браузера/простой проверки, но для DRF + JWT обычно лучше **API-first** (см. ниже).

### 1.2. API-first (рекомендуемый вариант для DRF + JWT)
API-first endpoints не делают редирект автоматически (кроме случая когда ты сам открываешь auth_url в браузере).
Они возвращают **JSON** и позволяют фронтенду контролировать поток (SPA/mobile).

Роуты (пример структуры из проекта):

- `GET /api/auth/social/api/login/<backend>/`  
  Возвращает JSON вида:
  ```json
  {
    "authorization_url": "https://provider...",
    "redirect_uri": "http://127.0.0.1:8000/api/auth/social/api/complete/<backend>/"
  }
  ```

- `GET /api/auth/social/api/complete/<backend>/?code=...&state=...`  
  Возвращает JWT и user-данные (пример):
  ```json
  {
    "access": "...",
    "refresh": "...",
    "user": {"id": 1, "username": "oauthuser", "email": "oauth@example.com"}
  }
  ```

> В проекте `complete` endpoint для API-first сделан **GET-only** — это важно для тестов и для проверки вручную.

---

## 2) Настройки, которые должны быть включены

### 2.1. requirements
Должны быть установлены зависимости:

```bash
pip install social-auth-app-django
```

(в проекте это уже добавлено в `requirements.txt` согласно stage 9.3 коммитам)

### 2.2. INSTALLED_APPS
В `config/settings.py`:

- `"social_django"` должен быть в `INSTALLED_APPS`.

### 2.3. Middleware + context processors
Рекомендовано (и у тебя уже включено):

- `social_django.middleware.SocialAuthExceptionMiddleware` в `MIDDLEWARE`
- context processors:
  - `social_django.context_processors.backends`
  - `social_django.context_processors.login_redirect`

### 2.4. AUTHENTICATION_BACKENDS
В `config/settings.py` должны быть backend’и провайдеров и стандартный Django backend:

```python
AUTHENTICATION_BACKENDS = (
    "social_core.backends.google.GoogleOAuth2",
    "social_core.backends.github.GithubOAuth2",
    "django.contrib.auth.backends.ModelBackend",
)
```

### 2.5. Credentials в settings
**Ключи читаются из Django settings**, поэтому переменные должны быть явно присвоены:

```python
SOCIAL_AUTH_GITHUB_KEY = os.getenv("SOCIAL_AUTH_GITHUB_KEY", "")
SOCIAL_AUTH_GITHUB_SECRET = os.getenv("SOCIAL_AUTH_GITHUB_SECRET", "")

SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.getenv("SOCIAL_AUTH_GOOGLE_OAUTH2_KEY", "")
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.getenv("SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET", "")
```

Проверка:

```bash
python manage.py shell -c "from django.conf import settings; print('GOOGLE=', settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY); print('GITHUB=', settings.SOCIAL_AUTH_GITHUB_KEY)"
```

Если Google выдаёт **“Missing required parameter: client_id”** — значит `SOCIAL_AUTH_GOOGLE_OAUTH2_KEY` пустой/не подхватился.

---

## 3) Критично важное: Sessions для параметра state

Ошибка вида:
- `Session data corrupted`
- `Missing needed parameter state`

обычно означает одно из двух:

1) ты открыл **complete URL напрямую**, минуя login URL (state не был создан),
2) сессии нестабильны/не сохраняются.

Минимально стабильный блок в `settings.py` (у тебя уже добавлен):

```python
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
```

И **вход всегда начинать с**:

- `/api/auth/social/login/<backend>/` (classic)
- `/api/auth/social/api/login/<backend>/` (API-first — получаешь authorization_url)

---

## 4) Redirect URI: что нужно указать у провайдера

### 4.1. Важно про порты (локально vs Docker)
- Локальный dev (runserver): `http://127.0.0.1:8000`
- Docker Compose (если проброшено на 8001): `http://127.0.0.1:8001`

Redirect URI должен совпадать **1-в-1** с тем, что реально использует backend.

### 4.2. Redirect URI для classic redirect-flow
- GitHub:
  - `http://127.0.0.1:8000/api/auth/social/complete/github/`
  - (Docker) `http://127.0.0.1:8001/api/auth/social/complete/github/`
- Google:
  - `http://127.0.0.1:8000/api/auth/social/complete/google-oauth2/`
  - (Docker) `http://127.0.0.1:8001/api/auth/social/complete/google-oauth2/`

### 4.3. Redirect URI для API-first
Это **ключевой момент**: если использовать API-first, callback должен указывать на `api/complete/...`

- GitHub (API-first):
  - `http://127.0.0.1:8000/api/auth/social/api/complete/github/`
  - (Docker) `http://127.0.0.1:8001/api/auth/social/api/complete/github/`
- Google (API-first):
  - `http://127.0.0.1:8000/api/auth/social/api/complete/google-oauth2/`
  - (Docker) `http://127.0.0.1:8001/api/auth/social/api/complete/google-oauth2/`

> **GitHub OAuth App** обычно позволяет **только один** callback URL.  
> Если нужна поддержика и classic, и API-first параллельно — проще завести **2 отдельные GitHub OAuth Apps**.

---

## 5) Как получить ключи (GitHub + Google)

### 5.1 GitHub OAuth App
1) GitHub → Settings → Developer settings → OAuth Apps → New OAuth App
2) Заполни:
   - **Application name**: любое (например `RetailProcurement Local`)
   - **Homepage URL**: `http://127.0.0.1:8000`
   - **Authorization callback URL**:
     - API-first: `http://127.0.0.1:8000/api/auth/social/api/complete/github/`
     - или classic: `http://127.0.0.1:8000/api/auth/social/complete/github/`
3) После создания:
   - `Client ID` → это `SOCIAL_AUTH_GITHUB_KEY`
   - `Client Secret` (Generate a new client secret) → это `SOCIAL_AUTH_GITHUB_SECRET`

В `.env` / `.env.docker`:

```bash
SOCIAL_AUTH_GITHUB_KEY=...
SOCIAL_AUTH_GITHUB_SECRET=...
```

### 5.2 Google OAuth Client ID (Google Cloud)
1) Google Cloud Console → APIs & Services → Credentials
2) Create Credentials → OAuth client ID
3) Application type: **Web application**
4) Заполни:
   - **Authorized JavaScript origins**:  
     `http://127.0.0.1:8000` (и/или `http://127.0.0.1:8001` для Docker)
   - **Authorized redirect URIs** (можно несколько):
     - API-first: `http://127.0.0.1:8000/api/auth/social/api/complete/google-oauth2/`
     - classic: `http://127.0.0.1:8000/api/auth/social/complete/google-oauth2/`
5) После создания:
   - `Client ID` → `SOCIAL_AUTH_GOOGLE_OAUTH2_KEY`
   - `Client Secret` → `SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET`

В `.env` / `.env.docker`:

```bash
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY=...
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET=...
```

---

## 6) Проверочные запросы (manual smoke)

### 6.1 Classic redirect-flow (через браузер)
Открывай **login URL**, а не complete:

- GitHub:  
  ```text
  http://127.0.0.1:8000/api/auth/social/login/github/
  ```
- Google:  
  ```text
  http://127.0.0.1:8000/api/auth/social/login/google-oauth2/
  ```

После подтверждения провайдер сам вернёт на:

- `/api/auth/social/complete/<backend>/?code=...&state=...`

### 6.2 API-first flow (через curl + браузер)
1) Получить authorization_url:

```bash
curl -s "http://127.0.0.1:8000/api/auth/social/api/login/github/" | jq
```

2) Открыть `authorization_url` в браузере (или на фронте сделать redirect).
3) Провайдер вернёт на callback:

```text
http://127.0.0.1:8000/api/auth/social/api/complete/github/?code=...&state=...
```

4) На callback вернётся JSON с JWT (access/refresh).

---

## 7) Тесты (без реального GitHub/Google)
Тесты API-first сделаны так, чтобы НЕ зависеть от внешних провайдеров:

- monkeypatch `load_strategy`, `load_backend`
- dummy backend возвращает `auth_url()` и `complete()`

Запуск:

```bash
pytest -q tests/test_social_api_first.py
```

---

## 8) Частые ошибки и быстрый чек-лист

### Ошибка: `Missing required parameter: client_id` (Google)
- ключ `SOCIAL_AUTH_GOOGLE_OAUTH2_KEY` пустой/не подхватился
- проверь через `python manage.py shell ... settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY`

### Ошибка: `Missing needed parameter state`
- ты открыл `complete` напрямую (без `login`)
- либо сессии не работают (см. Sessions block)

### Ошибка: Redirect URI mismatch
- callback URL у провайдера не совпадает с тем, что реально используется
- проверь порт (8000 vs 8001) и путь:
  - classic: `/api/auth/social/complete/.../`
  - api-first: `/api/auth/social/api/complete/.../`

---

## 9) Где что лежит в проекте
- `config/settings.py` — настройки social-auth + session
- `config/urls.py` — подключение `social_django.urls`
- `apps/users/social_api.py` — реализация API-first login/complete
- `tests/test_social_api_first.py` — тесты API-first endpoints (monkeypatch load_backend)

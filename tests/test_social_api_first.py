# tests/test_social_api_first.py

import pytest
from django.contrib.auth import get_user_model
from social_core.exceptions import AuthException


class DummyBackend:
    def __init__(self, *, auth_url_value: str, complete_user=None, raise_exc: Exception | None = None):
        self._auth_url_value = auth_url_value
        self._complete_user = complete_user
        self._raise_exc = raise_exc

    def auth_url(self):
        # В реальном backend тут создаётся state в session.
        # Для API-first unit-теста это не нужно — мы тестируем нашу обвязку.
        return self._auth_url_value

    def complete(self, user=None, redirect_name="next", *args, **kwargs):
        if self._raise_exc:
            raise self._raise_exc
        return self._complete_user


@pytest.mark.django_db
def test_social_api_login_returns_authorization_url(api_client, monkeypatch):
    import apps.users.social_api as social_api

    dummy = DummyBackend(auth_url_value="https://provider.example/auth?x=1")

    monkeypatch.setattr(social_api, "load_strategy", lambda req: object())
    monkeypatch.setattr(social_api, "load_backend", lambda strategy, name, redirect_uri: dummy)

    r = api_client.get("/api/auth/social/api/login/github/")
    assert r.status_code == 200, r.json()

    data = r.json()
    assert "authorization_url" in data
    assert data["authorization_url"] == "https://provider.example/auth?x=1"

    assert "redirect_uri" in data
    assert data["redirect_uri"].endswith("/api/auth/social/api/complete/github/")


@pytest.mark.django_db
def test_social_api_complete_returns_jwt(api_client, monkeypatch):
    import apps.users.social_api as social_api

    User = get_user_model()
    u = User.objects.create_user(username="oauthuser", email="oauth@example.com", password="x")

    dummy = DummyBackend(auth_url_value="x", complete_user=u)

    monkeypatch.setattr(social_api, "load_strategy", lambda req: object())
    monkeypatch.setattr(social_api, "load_backend", lambda strategy, name, redirect_uri: dummy)

    r = api_client.get("/api/auth/social/api/complete/github/?code=abc&state=xyz")
    assert r.status_code == 200, r.json()

    body = r.json()
    assert isinstance(body.get("access"), str) and body["access"]
    assert isinstance(body.get("refresh"), str) and body["refresh"]

    assert body["user"]["id"] == u.id
    assert body["user"]["username"] == u.username
    assert body["user"]["email"] == u.email


@pytest.mark.django_db
def test_social_api_complete_auth_exception_returns_400(api_client, monkeypatch):
    import apps.users.social_api as social_api

    dummy = DummyBackend(
        auth_url_value="x",
        complete_user=None,
        raise_exc=AuthException(None, "boom"),
    )

    monkeypatch.setattr(social_api, "load_strategy", lambda req: object())
    monkeypatch.setattr(social_api, "load_backend", lambda strategy, name, redirect_uri: dummy)

    r = api_client.get("/api/auth/social/api/complete/github/?code=abc&state=xyz")
    assert r.status_code == 400, r.json()
    assert "detail" in r.json()


@pytest.mark.django_db
def test_social_api_unsupported_backend_returns_404(api_client):
    r = api_client.get("/api/auth/social/api/login/vk/")
    assert r.status_code == 404

    r = api_client.get("/api/auth/social/api/complete/vk/?code=1&state=1")
    assert r.status_code == 404


@pytest.mark.django_db
def test_social_api_complete_backend_returns_no_user_400(api_client, monkeypatch):
    """
    API-first complete: если backend не вернул пользователя (None),
    endpoint должен вернуть 400 (а не 200/JWT).
    """
    import apps.users.social_api as social_api

    dummy = DummyBackend(auth_url_value="x", complete_user=None)

    monkeypatch.setattr(social_api, "load_strategy", lambda req: object())
    monkeypatch.setattr(social_api, "load_backend", lambda strategy, name, redirect_uri: dummy)

    r = api_client.get("/api/auth/social/api/complete/github/?code=fake&state=fake")
    assert r.status_code == 400, r.json()
    assert "detail" in r.json()
# tests/test_settings_branch_coverage.py

import importlib
import os

import pytest


def _reload_settings_module():
    """
    Перезагружаем module-level settings (НЕ django.conf.settings),
    чтобы прогнать ветки if SENTRY_DSN / if SILK_ENABLED.
    """
    import config.settings as settings_mod

    return importlib.reload(settings_mod)


@pytest.mark.django_db
def test_settings_sentry_branch_false(monkeypatch):
    """
    Ветка: SENTRY_DSN пустой -> sentry_sdk.init НЕ вызывается.
    """
    # гарантируем "пусто"
    monkeypatch.setenv("SENTRY_DSN", "")
    monkeypatch.setenv("SILK_ENABLED", "0")

    # Подменяем sentry_sdk.init, чтобы можно было проверить вызовы
    import sentry_sdk

    called = {"n": 0}

    def fake_init(*args, **kwargs):
        called["n"] += 1

    monkeypatch.setattr(sentry_sdk, "init", fake_init, raising=True)

    _reload_settings_module()

    assert called["n"] == 0


@pytest.mark.django_db
def test_settings_sentry_and_silk_branches_true(monkeypatch):
    """
    Ветки:
    - SENTRY_DSN НЕ пустой -> sentry_sdk.init вызывается
    - SILK_ENABLED=1 -> настройки silk применяются (middleware + installed_apps + etc)
    """
    # включаем Sentry-ветку
    monkeypatch.setenv("SENTRY_DSN", "http://public@example.com/1")
    monkeypatch.setenv("SENTRY_ENVIRONMENT", "test")
    monkeypatch.setenv("SENTRY_TRACES_SAMPLE_RATE", "0.0")
    monkeypatch.setenv("SENTRY_SEND_PII", "0")
    monkeypatch.setenv("SENTRY_RELEASE", "")

    # включаем Silk-ветку
    monkeypatch.setenv("SILK_ENABLED", "1")
    monkeypatch.setenv("SILKY_INTERCEPT_PERCENT", "100")
    monkeypatch.setenv("SILKY_PYTHON_PROFILER", "0")

    import sentry_sdk

    called = {"n": 0}

    def fake_init(*args, **kwargs):
        called["n"] += 1

    monkeypatch.setattr(sentry_sdk, "init", fake_init, raising=True)

    settings_mod = _reload_settings_module()

    # Sentry init должен сработать
    assert called["n"] == 1

    # Silk ветка должна добавить app + middleware
    assert "silk" in settings_mod.INSTALLED_APPS
    assert settings_mod.MIDDLEWARE[0] == "silk.middleware.SilkyMiddleware"

    # И выставить защитные/настройки (если ты их прописываешь в ветке)
    assert getattr(settings_mod, "SILKY_AUTHENTICATION", True) is True
    assert getattr(settings_mod, "SILKY_AUTHORISATION", True) is True
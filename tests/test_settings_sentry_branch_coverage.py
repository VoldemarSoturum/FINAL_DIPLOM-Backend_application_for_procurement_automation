# tests/test_settings_sentry_branch_coverage.py

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest


def _exec_settings_as(module_name: str):
    base_dir = Path(__file__).resolve().parents[1]  # корень проекта (рядом с manage.py)
    settings_path = base_dir / "config" / "settings.py"

    spec = importlib.util.spec_from_file_location(module_name, settings_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.django_db
def test_settings_sentry_branch_both_sides(monkeypatch):
    """
    Закрываем обе стороны ветки:
      if SENTRY_DSN: ... else: (exit)

    1) SENTRY_DSN пустой -> ветка false (292->exit)
    2) SENTRY_DSN задан -> ветка true (инициализация sentry)
    """

    # --- 1) DSN пустой -> ветка false ---
    monkeypatch.setenv("SENTRY_DSN", "")
    _exec_settings_as("settings_sentry_off")

    # --- 2) DSN задан -> ветка true ---
    calls = {"init": 0}

    fake_sentry = ModuleType("sentry_sdk")

    def fake_init(*args, **kwargs):
        calls["init"] += 1

    fake_sentry.init = fake_init

    fake_integrations = ModuleType("sentry_sdk.integrations")
    fake_celery = ModuleType("sentry_sdk.integrations.celery")
    fake_django = ModuleType("sentry_sdk.integrations.django")

    class CeleryIntegration:
        pass

    class DjangoIntegration:
        pass

    fake_celery.CeleryIntegration = CeleryIntegration
    fake_django.DjangoIntegration = DjangoIntegration

    # Подсовываем фейки в sys.modules, чтобы import внутри settings.py взял их
    monkeypatch.setitem(sys.modules, "sentry_sdk", fake_sentry)
    monkeypatch.setitem(sys.modules, "sentry_sdk.integrations", fake_integrations)
    monkeypatch.setitem(sys.modules, "sentry_sdk.integrations.celery", fake_celery)
    monkeypatch.setitem(sys.modules, "sentry_sdk.integrations.django", fake_django)

    monkeypatch.setenv("SENTRY_DSN", "https://public@example.com/1")
    monkeypatch.setenv("SENTRY_ENVIRONMENT", "test")
    monkeypatch.setenv("SENTRY_RELEASE", "test-release")
    monkeypatch.setenv("SENTRY_TRACES_SAMPLE_RATE", "0.0")
    monkeypatch.setenv("SENTRY_SEND_PII", "0")

    _exec_settings_as("settings_sentry_on")

    assert calls["init"] == 1
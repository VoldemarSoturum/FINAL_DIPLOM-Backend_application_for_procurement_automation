# tests/test_settings_sentry_branch.py

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest


@pytest.mark.django_db
def test_settings_sentry_init_branch_executes(monkeypatch):
    """
    Закрываем branch в config/settings.py вида:

        SENTRY_DSN = os.getenv(...)
        if SENTRY_DSN:
            import sentry_sdk
            from sentry_sdk.integrations.celery import CeleryIntegration
            from sentry_sdk.integrations.django import DjangoIntegration
            sentry_sdk.init(...)

    Мы НЕ трогаем реальные django.conf.settings.
    Просто исполняем файл config/settings.py как отдельный модуль, но:
    - подставляем валидный SENTRY_DSN (чтобы if сработал)
    - подменяем sentry_sdk и его submodules на фейки (чтобы не было реальной инициализации)
    """
    # 1) env: включаем ветку
    monkeypatch.setenv("SENTRY_DSN", "https://public@example.com/1")
    monkeypatch.setenv("SENTRY_ENVIRONMENT", "test")
    monkeypatch.setenv("SENTRY_RELEASE", "test-release")
    monkeypatch.setenv("SENTRY_TRACES_SAMPLE_RATE", "0.0")
    monkeypatch.setenv("SENTRY_SEND_PII", "0")

    # 2) делаем фейковый sentry_sdk + integrations.*
    calls = {"init_called": 0}

    fake_sentry = ModuleType("sentry_sdk")

    def fake_init(*args, **kwargs):
        calls["init_called"] += 1

    fake_sentry.init = fake_init

    fake_integrations = ModuleType("sentry_sdk.integrations")
    fake_celery = ModuleType("sentry_sdk.integrations.celery")
    fake_django = ModuleType("sentry_sdk.integrations.django")

    class CeleryIntegration:  # noqa: D401
        pass

    class DjangoIntegration:  # noqa: D401
        pass

    fake_celery.CeleryIntegration = CeleryIntegration
    fake_django.DjangoIntegration = DjangoIntegration

    # Вкладываем в sys.modules, чтобы import внутри settings.py взял наши фейки
    monkeypatch.setitem(sys.modules, "sentry_sdk", fake_sentry)
    monkeypatch.setitem(sys.modules, "sentry_sdk.integrations", fake_integrations)
    monkeypatch.setitem(sys.modules, "sentry_sdk.integrations.celery", fake_celery)
    monkeypatch.setitem(sys.modules, "sentry_sdk.integrations.django", fake_django)

    # 3) исполняем config/settings.py как отдельный модуль (другим именем)
    base_dir = Path(__file__).resolve().parents[1]  # BASE_DIR проекта (рядом tests/)
    settings_path = base_dir / "config" / "settings.py"

    spec = importlib.util.spec_from_file_location("settings_sentry_test_module", settings_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)

    assert calls["init_called"] == 1
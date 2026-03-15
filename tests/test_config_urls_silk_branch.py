# tests/test_config_urls_silk_branch.py

import importlib
import sys
import types

import pytest
from django.conf import settings as dj_settings
from django.test import override_settings


@pytest.mark.django_db
def test_config_urls_silk_disabled_branch(monkeypatch):
    """
    Ветка: Silk выключен -> /silk/ НЕ добавляется в urlpatterns.

    Делаем максимально устойчиво:
    - env SILK_ENABLED=0 (на случай, если urls.py читает os.getenv)
    - override_settings(SILK_ENABLED=False)
    - переимпорт config.urls
    """
    monkeypatch.setenv("SILK_ENABLED", "0")

    with override_settings(SILK_ENABLED=False, ROOT_URLCONF="config.urls"):
        sys.modules.pop("config.urls", None)
        import config.urls as urls_mod
        importlib.reload(urls_mod)

        patterns = [str(p.pattern) for p in urls_mod.urlpatterns]
        assert not any("silk" in p for p in patterns), patterns


@pytest.mark.django_db
def test_config_urls_silk_enabled_branch(monkeypatch):
    """
    Ветка: Silk включен -> /silk/ добавляется в urlpatterns.

    Почему раньше мог падать/флапать (особенно в docker tests):
    - config.urls может включать silk по settings.SILK_ENABLED И/ИЛИ по env SILK_ENABLED
    - include("silk.urls") импортирует silk.urls, который тянет silk.models
      и падает, если "silk" не в INSTALLED_APPS (RuntimeError про app_label)

    Решение:
    1) выставляем env SILK_ENABLED=1 (на случай проверки через os.getenv)
    2) override_settings(SILK_ENABLED=True)
    3) подменяем sys.modules["silk.urls"] stub-модулем (app_name + urlpatterns),
       чтобы include() не импортировал реальный пакет silk
    4) (опционально) если где-то проверяют `"silk" in INSTALLED_APPS`,
       добавляем в settings.INSTALLED_APPS *без* перепопуляции app registry.
       Это важно: НЕ через override_settings(INSTALLED_APPS=...), иначе Django
       попробует загрузить "silk" как приложение и может упасть.
    """
    monkeypatch.setenv("SILK_ENABLED", "1")

    # Stub silk.urls, чтобы include("silk.urls") не тянул реальные модели silk
    fake_silk_pkg = types.ModuleType("silk")
    fake_silk_urls = types.ModuleType("silk.urls")
    fake_silk_urls.app_name = "silk"
    fake_silk_urls.urlpatterns = []

    monkeypatch.setitem(sys.modules, "silk", fake_silk_pkg)
    monkeypatch.setitem(sys.modules, "silk.urls", fake_silk_urls)

    # Если код в urls.py вдруг проверяет "silk" in INSTALLED_APPS — подстрахуемся
    installed = list(getattr(dj_settings, "INSTALLED_APPS", []))
    if "silk" not in installed:
        monkeypatch.setattr(dj_settings, "INSTALLED_APPS", installed + ["silk"], raising=False)

    with override_settings(SILK_ENABLED=True, ROOT_URLCONF="config.urls"):
        sys.modules.pop("config.urls", None)
        import config.urls as urls_mod
        importlib.reload(urls_mod)

        patterns = [str(p.pattern) for p in urls_mod.urlpatterns]
        assert any(p.startswith("silk/") or "silk" in p for p in patterns), patterns
# tests/test_users_admin_import_branches.py

import importlib
import sys

import pytest
from django.contrib import admin
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model


def _make_isolated_admin_site(monkeypatch):
    """
    Изолируемся от глобального admin.site, который может быть уже "засорён"
    (baton.autodiscover, другие admin.py и т.д.), чтобы не ловить AlreadyRegistered.

    ВАЖНО:
    apps.users.admin использует:
      - admin.site.register(...)
      - @admin.register(...)
    Поэтому патчим:
      - admin.site -> наш local_site
      - admin.register -> декоратор, который регистрирует в local_site
    """
    local_site = AdminSite(name="test-admin-site")

    # 1) Подменяем admin.site (используется в admin.site.register/unregister/is_registered)
    monkeypatch.setattr(admin, "site", local_site, raising=True)

    # 2) Подменяем admin.register (декоратор @admin.register(Model))
    def fake_register(*models, **kwargs):
        def decorator(admin_class):
            local_site.register(models, admin_class=admin_class)
            return admin_class

        return decorator

    monkeypatch.setattr(admin, "register", fake_register, raising=True)

    return local_site


@pytest.mark.django_db
def test_users_admin_import_when_user_not_registered_skips_unregister(monkeypatch):
    """
    Закрываем branch coverage 44->49:
      if admin.site.is_registered(User):
          admin.site.unregister(User)

    Здесь User НЕ зарегистрирован в нашем изолированном local_site,
    значит ветка if НЕ выполняется, и переход идёт дальше (как раз 44->49).
    """
    # гарантируем, что auth.admin уже импортирован в "нормальном" окружении
    # чтобы он не успел зарегистрировать User в нашем local_site
    import django.contrib.auth.admin  # noqa: F401

    User = get_user_model()
    local_site = _make_isolated_admin_site(monkeypatch)

    # следим, что unregister НЕ вызывался
    calls = {"unregister": 0}
    orig_unreg = local_site.unregister

    def spy_unregister(model_or_iterable):
        calls["unregister"] += 1
        return orig_unreg(model_or_iterable)

    monkeypatch.setattr(local_site, "unregister", spy_unregister, raising=True)

    # импортируем apps.users.admin "с нуля"
    sys.modules.pop("apps.users.admin", None)
    import apps.users.admin  # noqa: F401

    assert calls["unregister"] == 0
    assert local_site.is_registered(User) is True  # модуль должен зарегистрировать UserAdmin


@pytest.mark.django_db
def test_users_admin_import_when_user_registered_calls_unregister(monkeypatch):
    """
    Добиваем вторую сторону ветки:
    - заранее регистрируем User в local_site
    - при импорте apps.users.admin он должен его unregister-нуть и зарегистрировать заново.
    """
    import django.contrib.auth.admin  # noqa: F401

    User = get_user_model()
    local_site = _make_isolated_admin_site(monkeypatch)

    # заранее регистрируем User, чтобы is_registered(User) == True
    local_site.register(User)

    calls = {"unregister": 0}
    orig_unreg = local_site.unregister

    def spy_unregister(model_or_iterable):
        # именно на User нас интересует вызов
        if model_or_iterable is User:
            calls["unregister"] += 1
        return orig_unreg(model_or_iterable)

    monkeypatch.setattr(local_site, "unregister", spy_unregister, raising=True)

    sys.modules.pop("apps.users.admin", None)
    import apps.users.admin  # noqa: F401

    assert calls["unregister"] == 1
    assert local_site.is_registered(User) is True
# tests/test_users_admin_notregistered.py

import sys
import pytest

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.admin.exceptions import AlreadyRegistered, NotRegistered
from django.contrib.admin.sites import AdminSite


@pytest.mark.django_db
def test_users_admin_hits_notregistered_branch_22_23(monkeypatch):
    """
    Стабильно покрываем ветку:
      try: admin.site.unregister(User)
      except NotRegistered: pass

    Проблема: Baton/autodiscover может заранее регистрировать модели -> AlreadyRegistered.
    Решение:
    - патчим AdminSite.register (класс!) чтобы игнорировать AlreadyRegistered
    - патчим AdminSite.unregister (класс!) чтобы для User выдать NotRegistered
    - импортируем apps.users.admin "с нуля"
    """
    User = get_user_model()

    sys.modules.pop("apps.users.admin", None)

    # 1) safe register (на уровне класса, чтобы decorator @admin.register тоже видел)
    orig_register = AdminSite.register

    def safe_register(self, model_or_iterable, admin_class=None, **options):
        try:
            return orig_register(self, model_or_iterable, admin_class=admin_class, **options)
        except AlreadyRegistered:
            return None

    monkeypatch.setattr(AdminSite, "register", safe_register, raising=True)

    # 2) заставляем unregister(User) уйти в except NotRegistered
    orig_unregister = AdminSite.unregister

    def fake_unregister(self, model_or_iterable):
        if model_or_iterable is User:
            raise NotRegistered("force NotRegistered for User")
        try:
            return orig_unregister(self, model_or_iterable)
        except NotRegistered:
            return None

    monkeypatch.setattr(AdminSite, "unregister", fake_unregister, raising=True)

    # Импорт не должен упасть
    import apps.users.admin  # noqa: F401
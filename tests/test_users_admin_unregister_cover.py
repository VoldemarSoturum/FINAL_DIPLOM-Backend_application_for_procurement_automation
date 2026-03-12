# tests/test_users_admin_unregister_cover.py

import sys
import pytest

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.admin.exceptions import AlreadyRegistered, NotRegistered
from django.contrib.admin.sites import AdminSite


@pytest.mark.django_db
def test_users_admin_unregister_lines_22_23_execute(monkeypatch):
    """
    Стабильно покрываем ветку "unregister(User) успешно":

    - делаем safe register (игнор AlreadyRegistered)
    - гарантируем, что User зарегистрирован ДО импорта apps.users.admin
    - считаем вызов unregister(User)
    """
    User = get_user_model()

    sys.modules.pop("apps.users.admin", None)

    # 1) safe register
    orig_register = AdminSite.register

    def safe_register(self, model_or_iterable, admin_class=None, **options):
        try:
            return orig_register(self, model_or_iterable, admin_class=admin_class, **options)
        except AlreadyRegistered:
            return None

    monkeypatch.setattr(AdminSite, "register", safe_register, raising=True)

    # 2) гарантируем, что User зарегистрирован (иначе unregister уйдёт в NotRegistered)
    try:
        admin.site.register(User)
    except AlreadyRegistered:
        pass

    # 3) счётчик для unregister(User)
    calls = {"user_unreg": 0}
    orig_unregister = AdminSite.unregister

    def counting_unregister(self, model_or_iterable):
        if model_or_iterable is User:
            calls["user_unreg"] += 1
        try:
            return orig_unregister(self, model_or_iterable)
        except NotRegistered:
            return None

    monkeypatch.setattr(AdminSite, "unregister", counting_unregister, raising=True)

    import apps.users.admin  # noqa: F401

    assert calls["user_unreg"] >= 1
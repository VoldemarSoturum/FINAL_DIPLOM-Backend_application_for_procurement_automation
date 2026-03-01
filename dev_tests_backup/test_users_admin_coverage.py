import importlib

import pytest
from django.contrib import admin
from django.contrib.admin.sites import AlreadyRegistered, NotRegistered


@pytest.mark.django_db
def test_users_admin_notregistered_branch(monkeypatch):
    """
    Покрываем ветку except admin.sites.NotRegistered в apps/users/admin.py
    через reload модуля с подменой admin.site.unregister.
    """

    import apps.users.admin as users_admin  # module already imported once in normal flow

    orig_register = admin.site.register

    def raise_notregistered(model):
        raise NotRegistered("not registered")

    def safe_register(*args, **kwargs):
        try:
            return orig_register(*args, **kwargs)
        except AlreadyRegistered:
            return None

    monkeypatch.setattr(admin.site, "unregister", raise_notregistered)
    monkeypatch.setattr(admin.site, "register", safe_register)

    importlib.reload(users_admin)
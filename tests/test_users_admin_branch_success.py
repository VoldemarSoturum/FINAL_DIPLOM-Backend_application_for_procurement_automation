import importlib

import pytest
from django.contrib import admin
from django.contrib.admin.sites import AlreadyRegistered


@pytest.mark.django_db
def test_users_admin_unregister_success_branch(monkeypatch):
    import apps.users.admin as users_admin

    # unregister должен отработать "успешно"
    monkeypatch.setattr(admin.site, "unregister", lambda model: None)

    # register не должен падать при reload (на AlreadyRegistered)
    orig_register = admin.site.register

    def safe_register(*args, **kwargs):
        try:
            return orig_register(*args, **kwargs)
        except AlreadyRegistered:
            return None

    monkeypatch.setattr(admin.site, "register", safe_register)

    importlib.reload(users_admin)
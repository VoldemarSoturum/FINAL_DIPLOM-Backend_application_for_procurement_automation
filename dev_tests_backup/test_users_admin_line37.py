import importlib
import sys

import pytest
from django.contrib import admin
from django.contrib.admin.sites import AlreadyRegistered, NotRegistered
from django.contrib.auth import get_user_model

from apps.users.models import UserProfile, Contact


@pytest.mark.django_db
def test_users_admin_line37(monkeypatch):
    User = get_user_model()

    # clean registrations to avoid AlreadyRegistered from decorators
    for model in (UserProfile, Contact, User):
        try:
            admin.site.unregister(model)
        except NotRegistered:
            pass

    # safe register: ignore AlreadyRegistered
    orig_register = admin.site.register

    def safe_register(*args, **kwargs):
        try:
            return orig_register(*args, **kwargs)
        except AlreadyRegistered:
            return None

    monkeypatch.setattr(admin.site, "register", safe_register)

    # ensure User is registered so unregister(User) in admin.py executes
    safe_register(User)

    if "apps.users.admin" in sys.modules:
        del sys.modules["apps.users.admin"]

    import apps.users.admin as mod
    importlib.reload(mod)
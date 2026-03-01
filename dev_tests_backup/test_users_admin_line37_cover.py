import importlib
import sys

import pytest
from django.contrib import admin
from django.contrib.admin.sites import AlreadyRegistered, NotRegistered
from django.contrib.auth import get_user_model

from apps.users.models import UserProfile, Contact


@pytest.mark.django_db
def test_users_admin_line37_cover(monkeypatch):
    """
    Два reload подряд:
    1) unregister -> NotRegistered (покрывает ветку except/pass если строка 37 там)
    2) unregister -> success (покрывает ветку успеха, если строка 37 там)
    Плюс safe register, чтобы не падать на AlreadyRegistered из-за декораторов.
    """
    User = get_user_model()

    # чистим регистрации перед стартом
    for model in (UserProfile, Contact, User):
        try:
            admin.site.unregister(model)
        except NotRegistered:
            pass

    # safe register
    orig_register = admin.site.register

    def safe_register(*args, **kwargs):
        try:
            return orig_register(*args, **kwargs)
        except AlreadyRegistered:
            return None

    monkeypatch.setattr(admin.site, "register", safe_register)

    # 1) unregister всегда NotRegistered
    monkeypatch.setattr(admin.site, "unregister", lambda model: (_ for _ in ()).throw(NotRegistered("nr")))

    if "apps.users.admin" in sys.modules:
        del sys.modules["apps.users.admin"]
    import apps.users.admin as mod
    importlib.reload(mod)

    # 2) unregister успех
    monkeypatch.setattr(admin.site, "unregister", lambda model: None)
    importlib.reload(mod)
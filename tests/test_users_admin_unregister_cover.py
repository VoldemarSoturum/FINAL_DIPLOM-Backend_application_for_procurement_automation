# tests/test_users_admin_unregister_cover.py

import sys
import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.admin.sites import AlreadyRegistered, NotRegistered

from apps.users.models import UserProfile, Contact


@pytest.mark.django_db
def test_users_admin_unregister_lines_22_23_execute():
    User = get_user_model()

    # 1) Убираем модели, которые apps.users.admin регистрирует, чтобы не словить AlreadyRegistered
    for m in (UserProfile, Contact):
        try:
            admin.site.unregister(m)
        except NotRegistered:
            pass

    # 2) Регистрируем User, чтобы unregister(User) в apps.users.admin прошёл по SUCCESS-ветке
    try:
        admin.site.register(User)
    except AlreadyRegistered:
        pass

    # 3) Перезагружаем модуль "с нуля"
    sys.modules.pop("apps.users.admin", None)
    import apps.users.admin  # noqa: F401
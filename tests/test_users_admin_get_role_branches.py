# tests/test_users_admin_get_role_branches.py

import pytest
from types import SimpleNamespace

from apps.users.admin import UserAdmin
from apps.users.models import UserProfile


@pytest.mark.django_db
def test_users_admin_get_role_with_and_without_profile():
    """
    Добиваем branch coverage для get_role:

    ВАЖНО:
    UserAdmin нельзя создавать как UserAdmin(model=None, admin_site=None),
    потому что Django Admin ожидает настоящий model._meta.

    Но метод get_role() не использует self вообще, поэтому мы вызываем его
    как "unbound method": UserAdmin.get_role(None, obj)

    Покрываем 3 ветки:
    1) profile есть и role есть
    2) profile отсутствует
    3) profile есть, но равен None
    """
    # 1) profile есть, role есть
    obj_with_profile = SimpleNamespace(profile=SimpleNamespace(role=UserProfile.Role.SUPPLIER))
    assert UserAdmin.get_role(None, obj_with_profile) == UserProfile.Role.SUPPLIER

    # 2) profile отсутствует вообще
    obj_without_profile_attr = SimpleNamespace()
    assert UserAdmin.get_role(None, obj_without_profile_attr) == "-"

    # 3) profile есть, но None
    obj_profile_is_none = SimpleNamespace(profile=None)
    assert UserAdmin.get_role(None, obj_profile_is_none) == "-"
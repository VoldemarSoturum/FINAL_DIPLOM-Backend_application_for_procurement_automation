import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model

from apps.users.admin import UserAdmin
from apps.users.models import UserProfile


@pytest.mark.django_db
def test_user_admin_get_role_returns_profile_role():
    User = get_user_model()
    ua = UserAdmin(User, admin.site)

    u = User.objects.create_user(username="u1", password="p")

    # profile auto-created by signal -> default role
    assert ua.get_role(u) in (UserProfile.Role.CLIENT, "client")

    # IMPORTANT: update the same cached related object (u.profile), not a new query instance
    prof = u.profile
    prof.role = UserProfile.Role.SUPPLIER
    prof.save(update_fields=["role"])

    assert ua.get_role(u) in (UserProfile.Role.SUPPLIER, "supplier")
# tests/test_userprofile_serializer_contacts_branches.py

import pytest
from types import SimpleNamespace

from django.contrib.auth import get_user_model

from apps.users.models import Contact, UserProfile
from apps.users.serializers import UserProfileSerializer


class _Mgr:
    def __init__(self, qs):
        self._qs = qs

    def all(self):
        return self._qs


@pytest.mark.django_db
def test_userprofile_serializer_get_contacts_branches():
    User = get_user_model()

    u = User.objects.create_user(username="u1", password="x", email="u1@test.local")
    # профиль создаётся сигналом, но если вдруг нет — подстрахуемся
    profile, _ = UserProfile.objects.get_or_create(user=u, defaults={"role": UserProfile.Role.CLIENT})

    Contact.objects.create(user=u, type="email", value="u1@test.local")

    ser = UserProfileSerializer()

    # 1) user is None -> []
    p_none = SimpleNamespace(user=None)
    assert ser.get_contacts(p_none) == []

    # 2) реальная ветка (contacts или contact_set) на настоящем user
    real = ser.get_contacts(profile)
    assert isinstance(real, list)
    assert len(real) == 1

    # 3) альтернативная ветка: создаём dummy user с “другим” related_name
    qs = Contact.objects.filter(user=u)
    if hasattr(u, "contacts"):
        dummy_user = SimpleNamespace(contact_set=_Mgr(qs))
    else:
        dummy_user = SimpleNamespace(contacts=_Mgr(qs))

    dummy_profile = SimpleNamespace(user=dummy_user)
    alt = ser.get_contacts(dummy_profile)
    assert isinstance(alt, list)
    assert len(alt) == 1
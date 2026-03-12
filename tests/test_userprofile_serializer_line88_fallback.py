# tests/test_userprofile_serializer_line88_fallback.py

import pytest
from types import SimpleNamespace

from apps.users.serializers import UserProfileSerializer


@pytest.mark.django_db
def test_userprofile_serializer_get_contacts_final_fallback_returns_empty_list():
    """
    Добиваем line 88 в apps/users/serializers.py:

    Ветка: user есть, но у него нет ни `contacts`, ни `contact_set`
    => должен сработать финальный return [].
    """

    user_stub = SimpleNamespace()  # НЕТ атрибутов contacts/contact_set
    profile_stub = SimpleNamespace(user=user_stub)

    ser = UserProfileSerializer()
    assert ser.get_contacts(profile_stub) == []
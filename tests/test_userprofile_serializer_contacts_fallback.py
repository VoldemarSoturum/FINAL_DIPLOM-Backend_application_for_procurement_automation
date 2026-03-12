# tests/test_userprofile_serializer_contacts_fallback.py

import pytest
from types import SimpleNamespace

from apps.users.serializers import UserProfileSerializer


@pytest.mark.django_db
def test_userprofile_serializer_get_contacts_fallback_contact_set_branch_executes():
    """
    Добиваем ветку в UserProfileSerializer.get_contacts():

    - user.contacts отсутствует
    - user.contact_set существует -> идём по fallback-ветке
    """

    class ContactSetStub:
        def all(self):
            return []  # нам важен сам проход по ветке, контакты не нужны

    class UserStub:
        # ВАЖНО: намеренно НЕ задаём атрибут `contacts`
        contact_set = ContactSetStub()

    profile_stub = SimpleNamespace(user=UserStub())

    ser = UserProfileSerializer()
    assert ser.get_contacts(profile_stub) == []
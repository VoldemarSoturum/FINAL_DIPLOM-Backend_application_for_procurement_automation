# tests/test_users_serializers_coverage.py

import io

import pytest
from django.test import override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIRequestFactory

from PIL import Image

from apps.users.serializers import UserProfileSerializer
from apps.users.models import Contact


def _make_valid_png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (1, 1), color=(0, 255, 0)).save(buf, format="PNG")
    return buf.getvalue()


@pytest.mark.django_db
def test_userprofile_serializer_avatar_and_contacts_branches(client_user, tmp_path):
    """
    Закрываем ветки:
    - avatar=None
    - avatar есть, но request в контексте отсутствует -> отдаём относительный URL
    - avatar есть + request есть -> отдаём absolute URL
    - contacts сериализуются
    """
    profile = client_user.profile

    # добавим контакт, чтобы отработал source="user.contacts" (или аналог)
    Contact.objects.create(user=client_user, type="phone", value="+123")

    # 1) avatar отсутствует
    s = UserProfileSerializer(profile)
    data = s.data
    assert "avatar" in data
    assert data["avatar"] is None

    # 2) avatar есть -> сохраним файл в tmp media
    with override_settings(MEDIA_ROOT=tmp_path, MEDIA_URL="/media/"):
        profile.avatar = SimpleUploadedFile("a.png", _make_valid_png_bytes(), content_type="image/png")
        profile.save(update_fields=["avatar"])

        # без request -> относительный url
        s2 = UserProfileSerializer(profile)
        d2 = s2.data
        assert isinstance(d2["avatar"], str) and d2["avatar"].startswith("/media/")

        # с request -> absolute url (testserver)
        factory = APIRequestFactory()
        req = factory.get("/api/profile/avatar/")
        s3 = UserProfileSerializer(profile, context={"request": req})
        d3 = s3.data
        assert d3["avatar"].startswith("http://testserver/media/")

        # contacts должны быть списком
        assert isinstance(d3["contacts"], list)
        assert len(d3["contacts"]) >= 1
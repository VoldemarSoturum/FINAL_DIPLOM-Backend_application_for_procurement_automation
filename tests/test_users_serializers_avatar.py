# tests/test_users_serializers_avatar.py

import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APIRequestFactory

from apps.users.models import UserProfile, Contact
from apps.users.serializers import UserProfileSerializer


def _make_valid_png_bytes() -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    img = Image.new("RGBA", (2, 2), (0, 0, 0, 255))
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.mark.django_db
def test_userprofile_serializer_avatar_none(client_user):
    """
    Ветка: avatar отсутствует -> serializer.avatar == None
    """
    profile, _ = UserProfile.objects.get_or_create(user=client_user)
    profile.avatar = None
    profile.save(update_fields=["avatar"])

    data = UserProfileSerializer(profile).data
    assert data["avatar"] is None


@pytest.mark.django_db
def test_userprofile_serializer_avatar_relative_no_request(tmp_path, client_user):
    """
    Ветка: avatar есть, но request нет -> отдаём относительный URL (/media/...)
    """
    profile, _ = UserProfile.objects.get_or_create(user=client_user)

    with override_settings(MEDIA_ROOT=tmp_path, MEDIA_URL="/media/"):
        profile.avatar = SimpleUploadedFile("a.png", _make_valid_png_bytes(), content_type="image/png")
        profile.save(update_fields=["avatar"])

        data = UserProfileSerializer(profile).data
        assert isinstance(data["avatar"], str)
        assert data["avatar"].startswith("/media/"), data["avatar"]


@pytest.mark.django_db
def test_userprofile_serializer_avatar_absolute_with_request(tmp_path, client_user):
    """
    Ветка: avatar есть и request в context -> build_absolute_uri(...)
    """
    profile, _ = UserProfile.objects.get_or_create(user=client_user)

    with override_settings(MEDIA_ROOT=tmp_path, MEDIA_URL="/media/"):
        profile.avatar = SimpleUploadedFile("a.png", _make_valid_png_bytes(), content_type="image/png")
        profile.save(update_fields=["avatar"])

        rf = APIRequestFactory()
        request = rf.get("/api/profile/")

        data = UserProfileSerializer(profile, context={"request": request}).data
        assert data["avatar"].startswith("http://testserver/media/"), data["avatar"]


@pytest.mark.django_db
def test_userprofile_serializer_contacts_source(client_user):
    """
    Дополнительно: покрываем участок, где contacts берутся из user.contacts (если так настроено).
    """
    profile, _ = UserProfile.objects.get_or_create(user=client_user)

    Contact.objects.create(user=client_user, type="phone", value="+123")
    Contact.objects.create(user=client_user, type="email", value="a@b.c")

    data = UserProfileSerializer(profile).data
    assert isinstance(data["contacts"], list)
    assert len(data["contacts"]) == 2
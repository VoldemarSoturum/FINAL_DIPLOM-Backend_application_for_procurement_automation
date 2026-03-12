# tests/test_users_tasks.py

import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from apps.users.models import UserProfile


def _make_valid_png_bytes() -> bytes:
    """
    Генерим валидный PNG через Pillow — стабильно локально и в Docker.
    """
    from PIL import Image

    buf = io.BytesIO()
    img = Image.new("RGBA", (2, 2), (0, 0, 255, 255))
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.mark.django_db
def test_warm_user_avatar_renditions_profile_not_found():
    import apps.users.tasks as tasks_mod

    res = tasks_mod.warm_user_avatar_renditions(profile_id=999999)
    assert res["Status"] is False
    assert "not found" in res["Error"].lower()


@pytest.mark.django_db
def test_warm_user_avatar_renditions_no_avatar(supplier_user):
    """
    profile есть, avatar пустой -> Status=False
    """
    import apps.users.tasks as tasks_mod

    profile, _ = UserProfile.objects.get_or_create(user=supplier_user)
    profile.avatar = None
    profile.save(update_fields=["avatar"])

    res = tasks_mod.warm_user_avatar_renditions(profile_id=profile.id)
    assert res["Status"] is False
    assert "not found" in res["Error"].lower()


@pytest.mark.django_db
def test_warm_user_avatar_renditions_success(monkeypatch, tmp_path, supplier_user):
    """
    Success path:
    - кладём avatar в MEDIA_ROOT=tmp_path
    - monkeypatch VersatileImageFieldWarmer
    - проверяем: warm вызван, clear вызван, ответ корректный
    """
    import apps.users.tasks as tasks_mod

    profile, _ = UserProfile.objects.get_or_create(user=supplier_user)

    png_bytes = _make_valid_png_bytes()

    with override_settings(MEDIA_ROOT=tmp_path, MEDIA_URL="/media/"):
        profile.avatar = SimpleUploadedFile("avatar.png", png_bytes, content_type="image/png")
        profile.save(update_fields=["avatar"])

        calls = {"warm": 0, "clear": 0, "args": None}

        class FakeWarmer:
            def __init__(self, instance_or_queryset, rendition_key_set, image_attr):
                calls["args"] = (instance_or_queryset.id, rendition_key_set, image_attr)

            def warm(self):
                calls["warm"] += 1
                return 5, ["fail1", "fail2"]  # num_created, failed_list

            def clear(self):
                calls["clear"] += 1

        monkeypatch.setattr(tasks_mod, "VersatileImageFieldWarmer", FakeWarmer, raising=True)

        res = tasks_mod.warm_user_avatar_renditions(profile_id=profile.id)

    assert res["Status"] is True
    assert res["created"] == 5
    assert res["failed"] == 2

    assert calls["warm"] == 1
    assert calls["clear"] == 1

    assert calls["args"][0] == profile.id
    assert calls["args"][1] == "avatar"
    assert calls["args"][2] == "avatar"
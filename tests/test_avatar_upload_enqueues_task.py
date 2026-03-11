import pytest
from types import SimpleNamespace
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.users.models import UserProfile


@pytest.mark.django_db
def test_avatar_upload_enqueues_warm_task(client_api, client_user, monkeypatch, django_capture_on_commit_callbacks):
    import apps.users.tasks as tasks_mod

    calls = {}

    def fake_delay(profile_id):
        calls["profile_id"] = profile_id
        return SimpleNamespace(id="task-1")

    monkeypatch.setattr(tasks_mod.warm_user_avatar_renditions, "delay", fake_delay)

    profile = UserProfile.objects.get(user=client_user)

    avatar = SimpleUploadedFile("a.png", b"\x89PNG\r\n\x1a\n", content_type="image/png")

    with django_capture_on_commit_callbacks(execute=True):
        r = client_api.patch("/api/profile/avatar/", {"avatar": avatar}, format="multipart")

    assert r.status_code == 200, r.json()
    assert calls.get("profile_id") == profile.id
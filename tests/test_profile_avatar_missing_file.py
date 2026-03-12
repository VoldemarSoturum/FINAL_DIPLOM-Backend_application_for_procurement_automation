# tests/test_profile_avatar_missing_file.py

import pytest


@pytest.mark.django_db
def test_profile_avatar_upload_requires_file(api_client, client_user):
    """
    Закрываем ветку в ProfileAvatarUploadAPIView.patch:
      if not file: return 400
    """
    api_client.force_authenticate(user=client_user)

    r = api_client.patch(
        "/api/profile/avatar/",
        data={},          # без FILES
        format="multipart"
    )

    assert r.status_code == 400, r.json()
    assert "detail" in r.json()
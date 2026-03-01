import pytest
from django.contrib.auth import get_user_model

from apps.users.models import UserProfile


@pytest.fixture()
def client_access(api_client, db):
    User = get_user_model()
    u = User.objects.create_user(username="client_contacts", password="client_pass", email="client_contacts@test.local")
    profile, _ = UserProfile.objects.get_or_create(user=u)
    profile.role = UserProfile.Role.CLIENT
    profile.save(update_fields=["role"])

    r = api_client.post("/api/auth/login/", {"username": "client_contacts", "password": "client_pass"}, format="json")
    assert r.status_code == 200
    token = r.json()["access"]
    return api_client, {"HTTP_AUTHORIZATION": f"Bearer {token}"}


@pytest.mark.django_db
def test_register_invalid_payload(api_client):
    r = api_client.post("/api/auth/register/", {"username": "", "email": "x@test.local", "password": "1"}, format="json")
    assert r.status_code == 400
    body = r.json()
    assert body["Status"] is False
    assert body["errors"]


@pytest.mark.django_db
def test_contacts_crud_and_not_found(client_access):
    client, headers = client_access

    # list empty
    r = client.get("/api/contacts/", **headers)
    assert r.status_code == 200
    assert r.json()["Status"] is True
    assert r.json()["data"]["contacts"] == []

    # create
    r = client.post("/api/contacts/", {"type": "phone", "value": "+491234567"}, format="json", **headers)
    assert r.status_code == 201
    body = r.json()
    assert body["Status"] is True
    contact_id = body["data"]["contact"]["id"]

    # list now 1
    r = client.get("/api/contacts/", **headers)
    assert r.status_code == 200
    assert len(r.json()["data"]["contacts"]) == 1

    # patch
    r = client.patch(f"/api/contacts/{contact_id}/", {"value": "+499999999"}, format="json", **headers)
    assert r.status_code == 200
    assert r.json()["data"]["contact"]["value"] == "+499999999"

    # delete
    r = client.delete(f"/api/contacts/{contact_id}/", **headers)
    assert r.status_code == 200
    assert r.json()["data"]["deleted"] is True

    # patch not found
    r = client.patch("/api/contacts/999999/", {"value": "x"}, format="json", **headers)
    assert r.status_code == 404
    assert r.json()["Status"] is False

    # delete not found
    r = client.delete("/api/contacts/999999/", **headers)
    assert r.status_code == 404
    assert r.json()["Status"] is False
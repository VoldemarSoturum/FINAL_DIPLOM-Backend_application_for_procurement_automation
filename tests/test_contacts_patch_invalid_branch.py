import pytest


@pytest.mark.django_db
def test_contacts_patch_invalid_branch(client_access):
    client, headers = client_access

    # создаём нормальный контакт
    r = client.post("/api/contacts/", {"type": "phone", "value": "+49111"}, format="json", **headers)
    assert r.status_code == 201
    contact_id = r.json()["data"]["contact"]["id"]

    # делаем PATCH с невалидным payload: пустой type
    r = client.patch(f"/api/contacts/{contact_id}/", {"type": ""}, format="json", **headers)
    assert r.status_code == 400
    assert r.json()["Status"] is False
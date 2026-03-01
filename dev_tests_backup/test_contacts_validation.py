import pytest


@pytest.mark.django_db
def test_contacts_create_validation_error(client_access):
    client, headers = client_access

    # missing value
    r = client.post("/api/contacts/", {"type": "phone"}, format="json", **headers)
    assert r.status_code == 400
    body = r.json()
    assert body["Status"] is False
    assert "value" in body["errors"]
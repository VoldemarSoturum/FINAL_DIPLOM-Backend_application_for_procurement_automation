import pytest


@pytest.mark.django_db
def test_health_endpoint_root_returns_ok(api_client):
    r = api_client.get("/")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
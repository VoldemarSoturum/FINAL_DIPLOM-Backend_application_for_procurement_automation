import pytest


class DummyResponse:
    def __init__(self, content: bytes, status_code: int):
        self.content = content
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


@pytest.mark.django_db
def test_importer_http_error_branch(supplier_api, monkeypatch):
    import apps.partners.services.importer as importer_mod

    monkeypatch.setattr(importer_mod.requests, "get", lambda url, timeout=20: DummyResponse(b"oops", 500))
    r = supplier_api.post("/api/partner/update/", {"url": "http://example.test/price.yaml"}, format="json")
    assert r.status_code in (400, 500)
    assert r.json()["Status"] is False


@pytest.mark.django_db
def test_importer_bad_yaml_branch(supplier_api, monkeypatch):
    import apps.partners.services.importer as importer_mod

    bad_yaml = b"::: this is not yaml :::"
    monkeypatch.setattr(importer_mod.requests, "get", lambda url, timeout=20: DummyResponse(bad_yaml, 200))

    r = supplier_api.post("/api/partner/update/", {"url": "http://example.test/price.yaml"}, format="json")
    assert r.status_code == 400
    assert r.json()["Status"] is False
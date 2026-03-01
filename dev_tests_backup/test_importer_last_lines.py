import pytest

from apps.partners.services.importer import import_price_from_url


class DummyResponse:
    def __init__(self, content: bytes, status_code: int = 200):
        self.content = content
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


@pytest.mark.django_db
def test_importer_yaml_safe_load_raises(monkeypatch, supplier_user):
    import apps.partners.services.importer as importer_mod

    monkeypatch.setattr(importer_mod.requests, "get", lambda url, timeout=20: DummyResponse(b"shop: X", 200))
    monkeypatch.setattr(importer_mod.yaml, "safe_load", lambda content: (_ for _ in ()).throw(ValueError("bad yaml")))

    res = import_price_from_url(user=supplier_user, url="http://example.test/bad.yaml")
    assert res["Status"] is False


@pytest.mark.django_db
def test_importer_yaml_safe_load_returns_none(monkeypatch, supplier_user):
    import apps.partners.services.importer as importer_mod

    monkeypatch.setattr(importer_mod.requests, "get", lambda url, timeout=20: DummyResponse(b"null", 200))
    monkeypatch.setattr(importer_mod.yaml, "safe_load", lambda content: None)

    res = import_price_from_url(user=supplier_user, url="http://example.test/null.yaml")
    assert res["Status"] is False
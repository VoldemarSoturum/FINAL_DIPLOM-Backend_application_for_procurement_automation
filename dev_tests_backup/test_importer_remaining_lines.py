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
def test_importer_requests_get_raises(monkeypatch, supplier_user):
    import apps.partners.services.importer as importer_mod

    def boom(*args, **kwargs):
        raise RuntimeError("timeout")

    monkeypatch.setattr(importer_mod.requests, "get", boom)

    res = import_price_from_url(user=supplier_user, url="http://example.test/boom.yaml")
    assert res["Status"] is False


@pytest.mark.django_db
def test_importer_safe_load_returns_list(monkeypatch, supplier_user):
    import apps.partners.services.importer as importer_mod

    monkeypatch.setattr(importer_mod.requests, "get", lambda url, timeout=20: DummyResponse(b"[]", 200))
    monkeypatch.setattr(importer_mod.yaml, "safe_load", lambda content: [])

    res = import_price_from_url(user=supplier_user, url="http://example.test/list.yaml")
    assert res["Status"] is False


@pytest.mark.django_db
def test_importer_good_with_unknown_category(monkeypatch, supplier_user):
    import apps.partners.services.importer as importer_mod

    yaml_payload = b"""
shop: TestShop
categories:
  - id: 1
    name: Phones
goods:
  - id: 1001
    category: 999
    name: BadCatProduct
    model: X
    price: 10.00
    quantity: 1
"""
    monkeypatch.setattr(importer_mod.requests, "get", lambda url, timeout=20: DummyResponse(yaml_payload, 200))

    # может вернуть Status True (пропустит товар) или False (строгая валидация) — главное: не падает
    res = import_price_from_url(user=supplier_user, url="http://example.test/unknown_cat.yaml")
    assert "Status" in res
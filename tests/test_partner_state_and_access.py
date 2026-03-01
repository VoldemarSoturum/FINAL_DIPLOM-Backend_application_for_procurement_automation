import pytest

from apps.catalog.models import Shop


@pytest.mark.django_db
def test_partner_state_blocks_import(supplier_api, monkeypatch):
    import apps.partners.services.importer as importer_mod

    yaml_payload = b"""
shop: TestShop
categories:
  - id: 1
    name: Phones
goods:
  - id: 1001
    category: 1
    name: iPhone 15
    model: A1
    price: 100.00
    quantity: 10
"""

    class DummyResponse:
        def __init__(self, content: bytes, status_code: int = 200):
            self.content = content
            self.status_code = status_code

        def raise_for_status(self):
            if self.status_code >= 400:
                raise RuntimeError(f"HTTP {self.status_code}")

    monkeypatch.setattr(importer_mod.requests, "get", lambda url, timeout=20: DummyResponse(yaml_payload, 200))

    # first import creates shop
    r = supplier_api.post("/api/partner/update/", {"url": "http://example.test/price.yaml"}, format="json")
    assert r.status_code == 200, r.data

    shop = Shop.objects.get(name="TestShop")

    # disable shop
    r = supplier_api.post("/api/partner/state/", {"state": False}, format="json")
    assert r.status_code == 200, r.data
    shop.refresh_from_db()
    assert shop.state is False

    # import must be blocked (3.4)
    r = supplier_api.post("/api/partner/update/", {"url": "http://example.test/price.yaml"}, format="json")
    assert r.status_code == 403, r.data

    # enable shop and import again
    r = supplier_api.post("/api/partner/state/", {"state": True}, format="json")
    assert r.status_code == 200, r.data
    r = supplier_api.post("/api/partner/update/", {"url": "http://example.test/price.yaml"}, format="json")
    assert r.status_code == 200, r.data
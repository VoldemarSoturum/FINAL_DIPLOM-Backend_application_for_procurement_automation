

import logging
import pytest

from apps.catalog.models import ProductInfo, Shop

logger = logging.getLogger(__name__)


class DummyResponse:
    def __init__(self, content: bytes, status_code: int = 200):
        self.content = content
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


@pytest.mark.django_db
def test_importer_upsert_and_zero_out(supplier_api, monkeypatch):
    import apps.partners.services.importer as importer_mod

    yaml_1 = b"""
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
    price_rrc: 120.00
    quantity: 10
    parameters:
      color: black
  - id: 1002
    category: 1
    name: Pixel 9
    model: P9
    price: 50.00
    quantity: 3
"""

    yaml_2 = b"""
shop: TestShop
categories:
  - id: 1
    name: Phones
goods:
  - id: 1001
    category: 1
    name: iPhone 15
    model: A1
    price: 110.00
    price_rrc: 130.00
    quantity: 8
    parameters:
      color: black
"""

    # import #1
    monkeypatch.setattr(importer_mod.requests, "get", lambda url, timeout=20: DummyResponse(yaml_1, 200))
    r = supplier_api.post("/api/partner/update/", {"url": "http://example.test/price.yaml"}, format="json")
    assert r.status_code == 200, r.data
    assert r.data["Status"] is True

    shop = Shop.objects.get(name="TestShop")
    assert shop.user is not None

    pi_1001 = ProductInfo.objects.get(shop=shop, external_id=1001)
    pi_1002 = ProductInfo.objects.get(shop=shop, external_id=1002)
    assert pi_1001.quantity == 10
    assert pi_1002.quantity == 3

    # import #2: update 1001 and remove 1002 -> quantity should become 0
    monkeypatch.setattr(importer_mod.requests, "get", lambda url, timeout=20: DummyResponse(yaml_2, 200))
    r = supplier_api.post("/api/partner/update/", {"url": "http://example.test/price2.yaml"}, format="json")
    assert r.status_code == 200, r.data
    assert r.data["Status"] is True

    pi_1001.refresh_from_db()
    pi_1002.refresh_from_db()

    assert str(pi_1001.price) == "110.00"
    assert pi_1001.quantity == 8
    assert pi_1002.quantity == 0  # zero-out missing
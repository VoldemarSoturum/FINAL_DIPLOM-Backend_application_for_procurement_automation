import logging
import pytest
from django.core import mail

from apps.catalog.models import ProductInfo

logger = logging.getLogger(__name__)


class DummyResponse:
    def __init__(self, content: bytes, status_code: int = 200):
        self.content = content
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


@pytest.mark.django_db
def test_smoke_import_basket_checkout_and_supplier_orders(supplier_api, client_api, monkeypatch):
    logger.info("Prepare YAML payload for importer")

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
    price_rrc: 120.00
    quantity: 10
    parameters:
      color: black
"""

    logger.info("Monkeypatch requests.get in importer")
    import apps.partners.services.importer as importer_mod
    monkeypatch.setattr(importer_mod.requests, "get", lambda url, timeout=20: DummyResponse(yaml_payload, 200))

    logger.info("Supplier calls /api/partner/update/")
    r = supplier_api.post("/api/partner/update/", {"url": "http://example.test/price.yaml"}, format="json")
    assert r.status_code == 200, r.data
    assert r.data["Status"] is True
    assert r.data["data"]["imported"] is True

    pi = ProductInfo.objects.first()
    assert pi is not None
    logger.info("Imported ProductInfo id=%s qty=%s", pi.id, pi.quantity)

    logger.info("Client adds ProductInfo to basket")
    r = client_api.post("/api/basket/items/", {"product_info_id": pi.id, "quantity": 2}, format="json")
    assert r.status_code == 200, r.data
    assert r.data["Status"] is True
    assert r.data["data"]["basket"]["items"], "Basket must contain items"

    logger.info("Client checkout basket")
    mail.outbox.clear()
    r = client_api.post("/api/basket/checkout/", {}, format="json")
    assert r.status_code == 200, r.data
    assert r.data["Status"] is True
    assert r.data["data"]["order"]["status"] == "new"

    logger.info("Verify emails: client + admin")
    assert len(mail.outbox) == 2

    logger.info("Supplier requests /api/partner/orders/")
    r = supplier_api.get("/api/partner/orders/")
    assert r.status_code == 200, r.data
    assert r.data["Status"] is True
    assert r.data["data"]["orders"], "Supplier must see at least one order"
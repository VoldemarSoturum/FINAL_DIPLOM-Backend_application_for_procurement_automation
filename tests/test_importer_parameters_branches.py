# tests/test_importer_parameters_branches.py

import pytest
import requests

from apps.partners.services.importer import import_price_from_url


class DummyResponse:
    def __init__(self, content: bytes, status_code: int = 200):
        self.content = content
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


@pytest.mark.django_db
def test_importer_parameters_branches(monkeypatch, supplier_user):
    import apps.partners.services.importer as importer_mod

    # 1-й товар: parameters НЕ dict (ветка soft-handling)
    # 2-й товар: parameters dict (нормальная обработка параметров)
    yaml_payload = b"""
shop: ParamShop
categories:
  - id: 1
    name: Phones
goods:
  - id: 1001
    category: 1
    name: BadParams
    model: B1
    price: 10.00
    price_rrc: 12.00
    quantity: 3
    parameters: "oops"
  - id: 1002
    category: 1
    name: GoodParams
    model: G1
    price: 20.00
    price_rrc: 25.00
    quantity: 5
    parameters:
      color: black
"""

    monkeypatch.setattr(importer_mod.requests, "get", lambda url, timeout=20: DummyResponse(yaml_payload, 200))

    result = import_price_from_url(user=supplier_user, url="http://example.test/price.yaml")
    assert result.get("Status") is True
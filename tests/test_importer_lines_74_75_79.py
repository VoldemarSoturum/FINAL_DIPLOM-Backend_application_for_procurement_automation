import pytest
import requests


class DummyResponse:
    def __init__(self, content: bytes, status_code: int = 200):
        self.content = content
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


@pytest.mark.django_db
def test_importer_bad_goods_item_hits_74_75(monkeypatch, supplier_user):
    import apps.partners.services.importer as imp

    # goods item без price => KeyError внутри try => ветка 74-75
    yaml_payload = b"""
shop: BadGoodsShop
categories:
  - id: 1
    name: Phones
goods:
  - id: 10
    category: 1
    name: X
    quantity: 1
"""
    monkeypatch.setattr(imp.requests, "get", lambda url, timeout=20: DummyResponse(yaml_payload, 200))

    res = imp.import_price_from_url(user=supplier_user, url="http://example.test/x.yaml")
    assert res["Status"] is False
    assert res["http_status"] == 400
    assert "Bad goods item" in str(res["Error"])


@pytest.mark.django_db
def test_importer_category_not_found_hits_79(monkeypatch, supplier_user):
    import apps.partners.services.importer as imp

    # category=999 отсутствует в categories => ветка 79
    yaml_payload = b"""
shop: CatMissingShop
categories:
  - id: 1
    name: Phones
goods:
  - id: 11
    category: 999
    name: X
    price: 10.00
    quantity: 1
"""
    monkeypatch.setattr(imp.requests, "get", lambda url, timeout=20: DummyResponse(yaml_payload, 200))

    res = imp.import_price_from_url(user=supplier_user, url="http://example.test/x.yaml")
    assert res["Status"] is False
    assert res["http_status"] == 400
    assert "Category id=999 not found" in str(res["Error"])
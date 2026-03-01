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
def test_importer_missing_required_keys(monkeypatch, supplier_user):
    """
    Пытаемся словить ветки проверок структуры YAML:
    - нет shop
    - нет categories/goods
    """
    import apps.partners.services.importer as importer_mod

    yaml_no_shop = b"""
categories:
  - id: 1
    name: Phones
goods: []
"""
    monkeypatch.setattr(importer_mod.requests, "get", lambda url, timeout=20: DummyResponse(yaml_no_shop, 200))
    res = import_price_from_url(user=supplier_user, url="http://example.test/no_shop.yaml")
    assert res["Status"] is False


@pytest.mark.django_db
def test_importer_goods_parameters_not_dict(monkeypatch, supplier_user):
    """
    Пытаемся закрыть ветки, где parameters отсутствует/не dict.
    """
    import apps.partners.services.importer as importer_mod

    yaml_bad_params = b"""
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
    quantity: 1
    parameters: [1,2,3]
"""
    monkeypatch.setattr(importer_mod.requests, "get", lambda url, timeout=20: DummyResponse(yaml_bad_params, 200))
    res = import_price_from_url(user=supplier_user, url="http://example.test/bad_params.yaml")
    assert res["Status"] is True  # импорт не должен падать из-за кривых parameters
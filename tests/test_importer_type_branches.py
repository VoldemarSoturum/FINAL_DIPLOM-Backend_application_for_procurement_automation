import pytest

from apps.catalog.models import Shop, Category, ProductInfo


class DummyResponse:
    def __init__(self, content: bytes, status_code: int = 200):
        self.content = content
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


@pytest.mark.django_db
def test_importer_categories_not_list_soft_handling(supplier_api, monkeypatch):
    """
    Если categories не list (dict), импортер может просто ничего не импортировать, но не падать.
    Проверяем мягкое поведение: Status True/200 и отсутствие категорий/товаров.
    """
    import apps.partners.services.importer as importer_mod

    yaml_payload = b"""
shop: TestShop
categories: {}
goods: []
"""
    monkeypatch.setattr(importer_mod.requests, "get", lambda url, timeout=20: DummyResponse(yaml_payload, 200))

    r = supplier_api.post("/api/partner/update/", {"url": "http://example.test/x.yaml"}, format="json")
    assert r.status_code == 200, r.json()
    body = r.json()
    assert body["Status"] is True

    # shop должен появиться/обновиться
    assert Shop.objects.filter(name="TestShop").exists()
    # но категорий/товаров может не быть
    assert Category.objects.count() == 0
    assert ProductInfo.objects.count() == 0


@pytest.mark.django_db
def test_importer_goods_not_list_soft_handling(supplier_api, monkeypatch):
    """
    Если goods не list (dict), импортер может ничего не импортировать, но не падать.
    """
    import apps.partners.services.importer as importer_mod

    yaml_payload = b"""
shop: TestShop
categories:
  - id: 1
    name: Phones
goods: {}
"""
    monkeypatch.setattr(importer_mod.requests, "get", lambda url, timeout=20: DummyResponse(yaml_payload, 200))

    r = supplier_api.post("/api/partner/update/", {"url": "http://example.test/x.yaml"}, format="json")
    assert r.status_code == 200, r.json()
    body = r.json()
    assert body["Status"] is True

    assert Shop.objects.filter(name="TestShop").exists()
    # categories может быть создана, а товары — нет (зависит от реализации)
    # поэтому фиксируем самое важное: товары точно не созданы
    assert ProductInfo.objects.count() == 0


@pytest.mark.django_db
def test_importer_good_missing_required_fields_is_skipped_or_errors(supplier_api, monkeypatch):
    """
    Товар без обязательных полей: импортер либо пропустит, либо вернёт Status=False.
    В любом случае он не должен создавать ProductInfo.
    """
    import apps.partners.services.importer as importer_mod

    yaml_payload = b"""
shop: TestShop
categories:
  - id: 1
    name: Phones
goods:
  - id: 1001
    category: 1
"""
    monkeypatch.setattr(importer_mod.requests, "get", lambda url, timeout=20: DummyResponse(yaml_payload, 200))

    r = supplier_api.post("/api/partner/update/", {"url": "http://example.test/x.yaml"}, format="json")
    assert r.status_code in (200, 400), r.json()
    assert ProductInfo.objects.count() == 0
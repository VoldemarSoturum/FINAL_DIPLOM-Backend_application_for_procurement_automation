import pytest
import requests
import yaml

from django.contrib.auth import get_user_model

from apps.catalog.models import Shop, Category, ProductInfo
from apps.users.models import UserProfile


class DummyResponse:
    def __init__(self, content: bytes, status_code: int = 200):
        self.content = content
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


@pytest.mark.django_db
def test_importer_category_mapping_exception_hits_37_38(supplier_api, monkeypatch):
    import apps.partners.services.importer as importer_mod

    yaml_payload = b"""
shop: TestShop
categories:
  - id: 1
    name: Phones
  - id: bad
    name: Broken
goods: []
"""
    monkeypatch.setattr(importer_mod.requests, "get", lambda url, timeout=20: DummyResponse(yaml_payload, 200))

    r = supplier_api.post("/api/partner/update/", {"url": "http://example.test/x.yaml"}, format="json")
    assert r.status_code == 200, r.json()
    assert r.json()["Status"] is True


@pytest.mark.django_db
def test_importer_shop_belongs_to_another_supplier_hits_51(db, supplier_api, monkeypatch):
    import apps.partners.services.importer as importer_mod

    User = get_user_model()
    other = User.objects.create_user(username="other_sup", password="p", email="o@test.local")
    prof, _ = UserProfile.objects.get_or_create(user=other)
    prof.role = UserProfile.Role.SUPPLIER
    prof.save(update_fields=["role"])

    Shop.objects.create(name="TestShop", url="https://taken.test", state=True, user=other)

    yaml_payload = b"""
shop: TestShop
categories:
  - id: 1
    name: Phones
goods: []
"""
    monkeypatch.setattr(importer_mod.requests, "get", lambda url, timeout=20: DummyResponse(yaml_payload, 200))

    r = supplier_api.post("/api/partner/update/", {"url": "http://example.test/x.yaml"}, format="json")
    assert r.status_code == 403, r.json()
    assert r.json()["Status"] is False
    assert "belongs to another supplier" in str(r.json()["errors"]).lower()


@pytest.mark.django_db
def test_importer_requests_exception(monkeypatch, supplier_user):
    from apps.partners.services.importer import import_price_from_url
    import apps.partners.services.importer as importer_mod

    def boom(*args, **kwargs):
        raise requests.RequestException("network error")

    monkeypatch.setattr(importer_mod.requests, "get", boom)

    res = import_price_from_url(user=supplier_user, url="http://example.test/boom.yaml")
    assert res["Status"] is False


@pytest.mark.django_db
def test_importer_yaml_yamLError(monkeypatch, supplier_user):
    from apps.partners.services.importer import import_price_from_url
    import apps.partners.services.importer as importer_mod

    monkeypatch.setattr(importer_mod.requests, "get", lambda url, timeout=20: DummyResponse(b"shop: X", 200))
    monkeypatch.setattr(importer_mod.yaml, "safe_load", lambda content: (_ for _ in ()).throw(yaml.YAMLError("bad yaml")))

    res = import_price_from_url(user=supplier_user, url="http://example.test/bad.yaml")
    assert res["Status"] is False


@pytest.mark.django_db
def test_importer_categories_not_list_soft_handling(supplier_api, monkeypatch):
    import apps.partners.services.importer as importer_mod

    yaml_payload = b"""
shop: TestShop
categories: {}
goods: []
"""
    monkeypatch.setattr(importer_mod.requests, "get", lambda url, timeout=20: DummyResponse(yaml_payload, 200))

    r = supplier_api.post("/api/partner/update/", {"url": "http://example.test/x.yaml"}, format="json")
    assert r.status_code == 200, r.json()
    assert r.json()["Status"] is True

    assert Shop.objects.filter(name="TestShop").exists()
    assert Category.objects.count() == 0
    assert ProductInfo.objects.count() == 0


@pytest.mark.django_db
def test_importer_goods_not_list_soft_handling(supplier_api, monkeypatch):
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
    assert r.json()["Status"] is True
    assert ProductInfo.objects.count() == 0
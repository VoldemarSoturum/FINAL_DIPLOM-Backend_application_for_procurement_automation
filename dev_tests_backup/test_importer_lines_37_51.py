import pytest
from django.contrib.auth import get_user_model

from apps.catalog.models import Shop
from apps.users.models import UserProfile


class DummyResponse:
    def __init__(self, content: bytes, status_code: int = 200):
        self.content = content
        self.status_code = status_code

    def raise_for_status(self):
        # у тебя requests.get обычно без HTTP ошибок в этих кейсах
        return None


@pytest.mark.django_db
def test_importer_category_mapping_exception_hits_37_38(supplier_api, monkeypatch):
    """
    categories содержит плохой элемент => int(c["id"]) / c["name"] падает => except: continue (37-38)
    """
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
    """
    Предсоздаём Shop с user != текущий supplier => ветка 51.
    """
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
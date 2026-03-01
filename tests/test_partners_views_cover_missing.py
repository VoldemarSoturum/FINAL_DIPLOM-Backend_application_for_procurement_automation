import pytest

from apps.catalog.models import Shop


@pytest.mark.django_db
def test_partner_state_no_shop_bound_hits_178(supplier_api):
    # line 178: no shop bound
    r = supplier_api.post("/api/partner/state/", {"state": True}, format="json")
    assert r.status_code == 400, r.json()
    body = r.json()
    assert body["Status"] is False
    assert "No shop bound" in str(body["errors"])


@pytest.mark.django_db
def test_partner_shop_get_success_hits_199(supplier_api, supplier_user):
    # line 199: ok(...) in GET when shop exists
    Shop.objects.create(name="GetShop199", url="https://get199.test", state=True, user=supplier_user)

    r = supplier_api.get("/api/partner/shop/")
    assert r.status_code == 200, r.json()
    body = r.json()
    assert body["Status"] is True
    assert body["data"]["shop"] == "GetShop199"


@pytest.mark.django_db
def test_partner_shop_patch_no_shop_bound_hits_240(supplier_api):
    # line 240: PATCH when no shop bound -> 404
    r = supplier_api.patch("/api/partner/shop/", {"url": "https://x.test"}, format="json")
    assert r.status_code == 404, r.json()
    body = r.json()
    assert body["Status"] is False
    assert "No shop bound" in str(body["errors"])


@pytest.mark.django_db
def test_partner_shop_patch_same_name_url_none_hits_255_to_266_and_266_to_269(supplier_api, supplier_user):
    """
    Covers:
    - 255->266 : new_name == shop.name (skip conflict check branch)
    - 266->269 : new_url is None (skip url update branch)
    """
    Shop.objects.create(name="SameNameShop", url="https://same.test", state=True, user=supplier_user)

    r = supplier_api.patch("/api/partner/shop/", {"name": "SameNameShop"}, format="json")
    assert r.status_code == 200, r.json()
    body = r.json()
    assert body["Status"] is True
    assert body["data"]["shop"] == "SameNameShop"


@pytest.mark.django_db
def test_partner_shop_patch_change_name_hits_264(supplier_api, supplier_user):
    # line 264: shop.name = new_name
    shop = Shop.objects.create(name="OldName264", url="https://old264.test", state=True, user=supplier_user)

    r = supplier_api.patch("/api/partner/shop/", {"name": "NewName264"}, format="json")
    assert r.status_code == 200, r.json()
    assert r.json()["Status"] is True

    shop.refresh_from_db()
    assert shop.name == "NewName264"
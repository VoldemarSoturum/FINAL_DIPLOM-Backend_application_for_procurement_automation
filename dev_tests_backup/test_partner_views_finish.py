import pytest
from apps.catalog.models import Shop


@pytest.mark.django_db
def test_partner_shop_get_success_and_post_already_bound(supplier_api, supplier_user):
    # bind shop directly
    shop = Shop.objects.create(name="BoundShop", url="https://b.test", state=True, user=supplier_user)

    # GET success
    r = supplier_api.get("/api/partner/shop/")
    assert r.status_code == 200, r.json()
    assert r.json()["Status"] is True
    assert r.json()["data"]["shop"] == "BoundShop"

    # POST should be 409 already bound
    r = supplier_api.post("/api/partner/shop/", {"name": "AnotherShop", "url": "https://a.test"}, format="json")
    assert r.status_code == 409, r.json()
    assert r.json()["Status"] is False
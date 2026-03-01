import pytest
import apps.partners.views as partner_views

from django.utils import timezone

from apps.catalog.models import Shop, Category, Product
from apps.orders.models import Order, OrderItem


@pytest.mark.django_db
def test_partner_update_validation_and_import_fail(supplier_api, monkeypatch):
    # 400: url missing
    r = supplier_api.post("/api/partner/update/", {}, format="json")
    assert r.status_code == 400, r.json()
    body = r.json()
    assert body["Status"] is False
    assert "url" in body["errors"]

    # 400: importer fails (cover PartnerUpdateAPIView error branch)
    def fake_import(*args, **kwargs):
        return {"Status": False, "Error": "Boom", "http_status": 400}

    monkeypatch.setattr(partner_views, "import_price_from_url", fake_import)

    r = supplier_api.post("/api/partner/update/", {"url": "http://example.test/x.yaml"}, format="json")
    assert r.status_code == 400, r.json()
    body = r.json()
    assert body["Status"] is False
    assert "Boom" in str(body["errors"])


@pytest.mark.django_db
def test_partner_state_validation_missing_field(supplier_api, supplier_user):
    """
    В DRF BooleanField принимает строки типа "yes"/"true" как True,
    поэтому проверяем гарантированно невалидный кейс: отсутствует поле state.
    """
    # должен быть shop, иначе endpoint вернёт "No shop bound..."
    Shop.objects.create(name="StateShop", url="https://state.test", state=True, user=supplier_user)

    r = supplier_api.post("/api/partner/state/", {}, format="json")
    assert r.status_code == 400, r.json()
    body = r.json()
    assert body["Status"] is False
    assert "state" in body["errors"]


@pytest.mark.django_db
def test_partner_shop_bind_existing_free_shop_and_patch_conflict(supplier_api, supplier_user):
    # free shop exists with user=None
    Shop.objects.create(name="FreeShop", url="https://free.test", state=True)

    # bind existing free shop (covers bind branch)
    r = supplier_api.post("/api/partner/shop/", {"name": "FreeShop", "url": "https://bound.test"}, format="json")
    assert r.status_code == 200, r.json()
    assert r.json()["Status"] is True

    shop = Shop.objects.get(name="FreeShop")
    assert shop.user_id == supplier_user.id
    assert shop.url == "https://bound.test"

    # PATCH with url only (covers successful validate/return attrs path)
    r = supplier_api.patch("/api/partner/shop/", {"url": "https://updated.test"}, format="json")
    assert r.status_code == 200, r.json()
    assert r.json()["Status"] is True

    shop.refresh_from_db()
    assert shop.url == "https://updated.test"

    # create conflict name shop (no user needed)
    Shop.objects.create(name="ConflictName", url="https://c.test", state=True)

    # PATCH name conflict -> 409
    r = supplier_api.patch("/api/partner/shop/", {"name": "ConflictName"}, format="json")
    assert r.status_code == 409, r.json()
    assert r.json()["Status"] is False


@pytest.mark.django_db
def test_partner_orders_date_to_invalid_and_unit_price_none_branch(supplier_api, supplier_user, client_user):
    # supplier must have bound shop
    shop = Shop.objects.create(name="OrdersBranchShop", url="https://o.test", state=True, user=supplier_user)
    cat = Category.objects.create(name="OCat")
    product = Product.objects.create(category=cat, name="OPhone")

    # create order with OrderItem unit_price=None to cover that branch in partner/orders response
    order = Order.objects.create(user=client_user, status=Order.Status.NEW, dt=timezone.now())
    OrderItem.objects.create(order=order, product=product, shop=shop, quantity=1, unit_price=None, unit_price_rrc=None)

    # invalid date_to -> 400
    r = supplier_api.get("/api/partner/orders/?date_to=bad-date")
    assert r.status_code == 400, r.json()
    assert r.json()["Status"] is False

    # normal call returns order, and item has unit_price/total null
    r = supplier_api.get("/api/partner/orders/")
    assert r.status_code == 200, r.json()
    body = r.json()
    assert body["Status"] is True
    orders = body["data"]["orders"]
    assert len(orders) >= 1
    item = orders[0]["items"][0]
    assert item["unit_price"] is None
    assert item["total"] is None
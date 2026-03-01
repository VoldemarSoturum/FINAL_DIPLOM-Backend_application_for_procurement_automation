import pytest
from django.utils import timezone

from apps.catalog.models import Shop, Category, Product
from apps.orders.models import Order, OrderItem


@pytest.mark.django_db
def test_partner_ok_fail_helpers_are_executed():
    import apps.partners.views as pv

    resp = pv.ok({"x": 1}, http_status=201)
    assert resp.status_code == 201

    resp = pv.fail({"msg": "err"}, http_status=400)
    assert resp.status_code == 400


@pytest.mark.django_db
def test_partner_state_and_orders_no_shop_bound(supplier_api):
    # state without shop
    r = supplier_api.post("/api/partner/state/", {"state": True}, format="json")
    assert r.status_code == 400, r.json()
    assert r.json()["Status"] is False

    # orders without shop
    r = supplier_api.get("/api/partner/orders/")
    assert r.status_code == 400, r.json()
    assert r.json()["Status"] is False


@pytest.mark.django_db
def test_partner_shop_patch_branches_same_and_unique_name(supplier_api, supplier_user, client_user):
    """
    Закрываем ветки PATCH:
    - name == текущему (не должно идти в conflict-check)
    - name меняется на уникальное (ветка обновления)
    + заодно создаём orderitem для /partner/orders/ чтобы вычислялся total.
    """
    # create shop via API -> часто 201
    r = supplier_api.post("/api/partner/shop/", {"name": "PatchShopX", "url": "https://x.test"}, format="json")
    assert r.status_code in (200, 201), r.json()

    shop = Shop.objects.get(user=supplier_user)

    # PATCH same name + new url
    r = supplier_api.patch("/api/partner/shop/", {"name": shop.name, "url": "https://new.test"}, format="json")
    assert r.status_code == 200, r.json()
    assert r.json()["Status"] is True

    # PATCH unique rename
    r = supplier_api.patch("/api/partner/shop/", {"name": "PatchShopX2"}, format="json")
    assert r.status_code == 200, r.json()
    assert r.json()["Status"] is True

    shop.refresh_from_db()
    assert shop.name == "PatchShopX2"

    # create order+item with unit_price not None -> total branch
    cat = Category.objects.create(name="PCat")
    product = Product.objects.create(category=cat, name="PProd")
    order = Order.objects.create(user=client_user, status=Order.Status.NEW, dt=timezone.now())
    OrderItem.objects.create(order=order, product=product, shop=shop, quantity=2, unit_price="10.00", unit_price_rrc="12.00")

    r = supplier_api.get("/api/partner/orders/")
    assert r.status_code == 200, r.json()
    body = r.json()
    assert body["Status"] is True
    assert body["data"]["orders"]
    item = body["data"]["orders"][0]["items"][0]
    assert item["total"] is not None
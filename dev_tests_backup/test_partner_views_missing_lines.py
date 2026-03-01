import pytest
from types import SimpleNamespace

from apps.catalog.models import Shop, Category, Product
from apps.orders.models import Order, OrderItem
from apps.users.models import UserProfile


@pytest.mark.django_db
def test_check_supplier_function_branches():
    """
    Покрывает apps/partners/views.py:36-43 (check_supplier)
    """
    import apps.partners.views as pv

    # unauth
    req = SimpleNamespace(user=SimpleNamespace(is_authenticated=False))
    resp = pv.check_supplier(req)
    assert resp is not None
    assert resp.status_code == 403
    assert resp.data["Status"] is False

    # auth, но не supplier
    req = SimpleNamespace(
        user=SimpleNamespace(
            is_authenticated=True,
            profile=SimpleNamespace(role=UserProfile.Role.CLIENT),
        )
    )
    resp = pv.check_supplier(req)
    assert resp is not None
    assert resp.status_code == 403
    assert resp.data["Status"] is False

    # auth supplier -> None
    req = SimpleNamespace(
        user=SimpleNamespace(
            is_authenticated=True,
            profile=SimpleNamespace(role=UserProfile.Role.SUPPLIER),
        )
    )
    resp = pv.check_supplier(req)
    assert resp is None


@pytest.mark.django_db
def test_partner_shop_post_invalid_body_hits_214(supplier_api):
    """
    Покрывает apps/partners/views.py:214 (serializer invalid in PartnerShopAPIView.post)
    """
    r = supplier_api.post("/api/partner/shop/", {}, format="json")
    assert r.status_code == 400, r.json()
    assert r.json()["Status"] is False


@pytest.mark.django_db
def test_partner_shop_bind_existing_free_shop_without_url_hits_232(supplier_api):
    """
    Покрывает apps/partners/views.py:232 (shop.save(update_fields=["user"]) when url is empty)
    """
    Shop.objects.create(name="FreeShopNoUrl", url="https://free.test", state=True)  # user=None

    # url не передаём -> попадём в ветку save(update_fields=["user"])
    r = supplier_api.post("/api/partner/shop/", {"name": "FreeShopNoUrl"}, format="json")
    assert r.status_code == 200, r.json()
    assert r.json()["Status"] is True

    shop = Shop.objects.get(name="FreeShopNoUrl")
    assert shop.user_id is not None


@pytest.mark.django_db
def test_partner_orders_filters_date_from_to_and_two_items_branches(supplier_api, supplier_user, client_user):
    """
    Покрывает:
    - apps/partners/views.py:364 (date_from filter applied)
    - apps/partners/views.py:371 (date_to filter applied)
    - apps/partners/views.py:378->391 (ветки orders_map)
    """
    shop = Shop.objects.create(name="MapShop2", url="https://m.test", state=True, user=supplier_user)
    cat = Category.objects.create(name="MapCat2")
    p1 = Product.objects.create(category=cat, name="P1")
    p2 = Product.objects.create(category=cat, name="P2")

    order = Order.objects.create(user=client_user, status=Order.Status.NEW)
    OrderItem.objects.create(order=order, product=p1, shop=shop, quantity=1, unit_price="10.00", unit_price_rrc="12.00")
    OrderItem.objects.create(order=order, product=p2, shop=shop, quantity=2, unit_price="5.00", unit_price_rrc=None)

    today = order.dt.date().isoformat()
    r = supplier_api.get(f"/api/partner/orders/?status=new&date_from={today}&date_to={today}")
    assert r.status_code == 200, r.json()
    body = r.json()
    assert body["Status"] is True
    assert len(body["data"]["orders"][0]["items"]) == 2
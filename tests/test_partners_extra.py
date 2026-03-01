import pytest
from types import SimpleNamespace
from unittest.mock import Mock
from django.utils import timezone

from apps.catalog.models import Shop, Category, Product
from apps.orders.models import Order, OrderItem
from apps.users.models import UserProfile


@pytest.mark.django_db
def test_check_supplier_function_branches():
    import apps.partners.views as pv

    # unauth
    req = SimpleNamespace(user=SimpleNamespace(is_authenticated=False))
    resp = pv.check_supplier(req)
    assert resp.status_code == 403
    assert resp.data["Status"] is False

    # auth not supplier
    req = SimpleNamespace(
        user=SimpleNamespace(is_authenticated=True, profile=SimpleNamespace(role=UserProfile.Role.CLIENT))
    )
    resp = pv.check_supplier(req)
    assert resp.status_code == 403
    assert resp.data["Status"] is False

    # supplier -> ok
    req = SimpleNamespace(
        user=SimpleNamespace(is_authenticated=True, profile=SimpleNamespace(role=UserProfile.Role.SUPPLIER))
    )
    assert pv.check_supplier(req) is None


@pytest.mark.django_db
def test_partner_shop_post_invalid_body_hits_214(supplier_api):
    r = supplier_api.post("/api/partner/shop/", {}, format="json")
    assert r.status_code == 400, r.json()
    assert r.json()["Status"] is False


@pytest.mark.django_db
def test_partner_shop_bind_existing_free_shop_without_url_hits_232(supplier_api):
    Shop.objects.create(name="FreeShopNoUrl", url="https://free.test", state=True)  # user=None

    r = supplier_api.post("/api/partner/shop/", {"name": "FreeShopNoUrl"}, format="json")
    assert r.status_code == 200, r.json()
    assert r.json()["Status"] is True

    shop = Shop.objects.get(name="FreeShopNoUrl")
    assert shop.user_id is not None


@pytest.mark.django_db
def test_partner_shop_patch_line_274_direct_call(monkeypatch, supplier_user):
    """
    274 недостижима через HTTP из-за trim_whitespace у DRF CharField,
    поэтому вызываем patch() напрямую и подменяем сериализатор.
    """
    import apps.partners.views as pv

    Shop.objects.create(name="Line274Shop", url="https://old.test", state=True, user=supplier_user)

    fake_ser = Mock()
    fake_ser.is_valid.return_value = True
    fake_ser.validated_data = {"name": "   "}  # strip() -> ""

    monkeypatch.setattr(pv, "PartnerShopPatchSerializer", lambda data=None: fake_ser)

    req = SimpleNamespace(user=supplier_user, data={"name": "   "})
    resp = pv.PartnerShopAPIView().patch(req)

    assert resp.status_code == 400
    assert resp.data["Status"] is False
    assert "name cannot be empty" in str(resp.data["errors"])


@pytest.mark.django_db
def test_partner_orders_filters_date_from_to_and_two_items_branches(supplier_api, supplier_user, client_user):
    shop = Shop.objects.create(name="MapShop2", url="https://m.test", state=True, user=supplier_user)
    cat = Category.objects.create(name="MapCat2")
    p1 = Product.objects.create(category=cat, name="P1")
    p2 = Product.objects.create(category=cat, name="P2")

    order = Order.objects.create(user=client_user, status=Order.Status.NEW, dt=timezone.now())
    OrderItem.objects.create(order=order, product=p1, shop=shop, quantity=1, unit_price="10.00", unit_price_rrc="12.00")
    OrderItem.objects.create(order=order, product=p2, shop=shop, quantity=2, unit_price="5.00", unit_price_rrc=None)

    today = order.dt.date().isoformat()
    r = supplier_api.get(f"/api/partner/orders/?status=new&date_from={today}&date_to={today}")
    assert r.status_code == 200, r.json()
    body = r.json()
    assert body["Status"] is True
    assert len(body["data"]["orders"][0]["items"]) == 2
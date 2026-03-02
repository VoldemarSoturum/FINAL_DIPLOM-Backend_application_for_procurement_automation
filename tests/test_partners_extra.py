import pytest
from types import SimpleNamespace
from unittest.mock import Mock
from datetime import datetime, timezone as dt_timezone

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
    """
    ВАЖНО:
    - фильтры date_from/date_to работают через order__dt__date (на стороне БД),
      и при "timezone-краевых" временах (около полуночи) можно неожиданно получить orders=[]
    - поэтому ставим dt в фиксированную дату и безопасное время (12:00),
      чтобы дата точно совпала в Python и в Postgres.
    - status в query берём из order.status (ровно то, что реально хранится в БД),
      чтобы не зависеть от регистра/представления enum.
    """
    shop = Shop.objects.create(name="MapShop2", url="https://m.test", state=True, user=supplier_user)
    cat = Category.objects.create(name="MapCat2")
    p1 = Product.objects.create(category=cat, name="P1")
    p2 = Product.objects.create(category=cat, name="P2")

    # фиксируем дату и время, чтобы фильтры по dt__date не флапали
    fixed_dt = timezone.make_aware(datetime(2026, 1, 15, 12, 0, 0), dt_timezone.utc)

    order = Order.objects.create(user=client_user, status=Order.Status.NEW, dt=fixed_dt)

    OrderItem.objects.create(
        order=order,
        product=p1,
        shop=shop,
        quantity=1,
        unit_price="10.00",
        unit_price_rrc="12.00",
    )
    OrderItem.objects.create(
        order=order,
        product=p2,
        shop=shop,
        quantity=2,
        unit_price="5.00",
        unit_price_rrc=None,
    )

    date_str = "2026-01-15"
    status_str = order.status  # берём из БД, чтобы не зависеть от представления enum

    r = supplier_api.get(f"/api/partner/orders/?status={status_str}&date_from={date_str}&date_to={date_str}")
    assert r.status_code == 200, r.json()

    body = r.json()
    assert body["Status"] is True, body

    orders = body["data"]["orders"]
    assert isinstance(orders, list), body
    assert len(orders) >= 1, body

    our = next((o for o in orders if o.get("id") == order.id), None)
    assert our is not None, {"expected_order_id": order.id, "orders": orders}

    assert len(our["items"]) == 2, our
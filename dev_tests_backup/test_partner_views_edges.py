import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.catalog.models import Shop, Category, Product, ProductInfo
from apps.orders.models import Order, OrderItem
from apps.users.models import UserProfile


def make_supplier_client(db, username="sup_edge", password="sup_pass", email="sup@test.local"):
    User = get_user_model()
    u = User.objects.create_user(username=username, password=password, email=email)
    profile, _ = UserProfile.objects.get_or_create(user=u)
    profile.role = UserProfile.Role.SUPPLIER
    profile.save(update_fields=["role"])
    return u


@pytest.mark.django_db
def test_partner_shop_get_no_shop_bound(supplier_api):
    r = supplier_api.get("/api/partner/shop/")
    assert r.status_code == 404
    assert r.json()["Status"] is False


@pytest.mark.django_db
def test_partner_shop_create_then_second_create_conflict(supplier_api):
    r = supplier_api.post("/api/partner/shop/", {"name": "MyShop", "url": "https://my.test"}, format="json")
    assert r.status_code in (200, 201), r.json()
    r = supplier_api.post("/api/partner/shop/", {"name": "MyShop2", "url": "https://my2.test"}, format="json")
    assert r.status_code == 409
    assert r.json()["Status"] is False


@pytest.mark.django_db
def test_partner_shop_name_conflict_other_supplier(db, supplier_api):
    # другой поставщик уже занял имя
    other = make_supplier_client(db, username="sup_other", password="pass", email="o@test.local")
    Shop.objects.create(name="TakenName", url="https://taken.test", user=other, state=True)

    r = supplier_api.post("/api/partner/shop/", {"name": "TakenName", "url": "https://x.test"}, format="json")
    assert r.status_code == 409
    assert r.json()["Status"] is False


@pytest.mark.django_db
def test_partner_shop_patch_empty_payload_validation(supplier_api):
    # нужно иметь shop
    r = supplier_api.post("/api/partner/shop/", {"name": "PatchShop", "url": "https://p.test"}, format="json")
    assert r.status_code in (200, 201)

    # пустой PATCH должен дать 400 (validate in PartnerShopPatchSerializer)
    r = supplier_api.patch("/api/partner/shop/", {}, format="json")
    assert r.status_code == 400
    assert r.json()["Status"] is False


@pytest.mark.django_db
def test_partner_orders_invalid_date_filters_and_status_filter(db, supplier_api, client_api):
    # создаём shop поставщика
    r = supplier_api.post("/api/partner/shop/", {"name": "OrdersShop", "url": "https://o.test"}, format="json")
    assert r.status_code in (200, 201)

    shop = Shop.objects.get(name="OrdersShop")

    # создаём товары/позиции
    cat = Category.objects.create(name="OrdersCat")
    product = Product.objects.create(category=cat, name="OrdersPhone")
    ProductInfo.objects.create(
        product=product, shop=shop, external_id=1, model="O1",
        name="Offer", quantity=10, price="10.00", price_rrc="12.00"
    )

    # создадим 2 заказа разного статуса от client_api пользователя
    user = client_api.handler._force_user  # force_authenticate user from fixture
    o1 = Order.objects.create(user=user, status=Order.Status.NEW, dt=timezone.now())
    o2 = Order.objects.create(user=user, status=Order.Status.DONE, dt=timezone.now())
    OrderItem.objects.create(order=o1, product=product, shop=shop, quantity=1, unit_price="10.00", unit_price_rrc="12.00")
    OrderItem.objects.create(order=o2, product=product, shop=shop, quantity=1, unit_price="10.00", unit_price_rrc="12.00")

    # invalid date_from
    r = supplier_api.get("/api/partner/orders/?date_from=bad-date")
    assert r.status_code == 400
    assert r.json()["Status"] is False

    # status filter
    r = supplier_api.get("/api/partner/orders/?status=done")
    assert r.status_code == 200
    data = r.json()["data"]["orders"]
    assert len(data) == 1
    assert data[0]["status"] == "done"
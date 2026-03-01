import pytest
from django.utils import timezone

from apps.catalog.models import Category, Shop, Product, ProductInfo
from apps.orders.models import Order, OrderItem


@pytest.mark.django_db
def test_basket_items_validation_errors(client_api):
    # missing product_info_id
    r = client_api.post("/api/basket/items/", {"quantity": 1}, format="json")
    assert r.status_code == 400
    body = r.json()
    assert body["Status"] is False
    assert "product_info_id" in body["errors"]

    # patch invalid quantity (0)
    r = client_api.patch("/api/basket/items/1/", {"quantity": 0}, format="json")
    assert r.status_code == 400
    body = r.json()
    assert body["Status"] is False
    assert "quantity" in body["errors"]


@pytest.mark.django_db
def test_client_orders_list_contains_items(client_api):
    user = client_api.handler._force_user

    shop = Shop.objects.create(name="OrdersListShop", url="https://ols.test", state=True)
    cat = Category.objects.create(name="OrdersListCat")
    product = Product.objects.create(category=cat, name="OrdersListProduct")

    ProductInfo.objects.create(
        product=product,
        shop=shop,
        external_id=1,
        model="OL1",
        name="Offer",
        quantity=10,
        price="10.00",
        price_rrc="12.00",
    )

    order = Order.objects.create(user=user, status=Order.Status.NEW, dt=timezone.now())
    OrderItem.objects.create(
        order=order,
        product=product,
        shop=shop,
        quantity=2,
        unit_price="10.00",
        unit_price_rrc="12.00",
    )

    r = client_api.get("/api/orders/")
    assert r.status_code == 200
    body = r.json()
    assert body["Status"] is True
    orders = body["data"]["orders"]
    assert len(orders) == 1
    assert orders[0]["status"] == "new"
    assert isinstance(orders[0]["dt"], str)  # isoformat()
    assert len(orders[0]["items"]) == 1
    assert orders[0]["items"][0]["product_name"] == "OrdersListProduct"
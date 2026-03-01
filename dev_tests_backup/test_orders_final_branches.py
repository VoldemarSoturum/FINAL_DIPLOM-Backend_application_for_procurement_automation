import pytest

from apps.catalog.models import Category, Shop, Product, ProductInfo
from apps.orders.models import Order, OrderItem


@pytest.mark.django_db
def test_basket_add_same_item_twice_increments_quantity(client_api):
    """
    Закрывает ветку в BasketItemsAPIView.post: item created=False -> увеличение quantity.
    Это обычно и есть missing 119-120.
    """
    shop = Shop.objects.create(name="IncShop", url="https://inc.test", state=True)
    cat = Category.objects.create(name="IncCat")
    product = Product.objects.create(category=cat, name="IncProduct")
    pi = ProductInfo.objects.create(
        product=product, shop=shop, external_id=1, model="I",
        name="Offer", quantity=10, price="10.00", price_rrc="12.00"
    )

    r = client_api.post("/api/basket/items/", {"product_info_id": pi.id, "quantity": 1}, format="json")
    assert r.status_code == 200, r.json()
    r = client_api.post("/api/basket/items/", {"product_info_id": pi.id, "quantity": 2}, format="json")
    assert r.status_code == 200, r.json()

    basket = r.json()["data"]["basket"]
    assert basket["items"][0]["quantity"] == 3


@pytest.mark.django_db
def test_client_orders_list_item_with_null_prices(client_api):
    """
    Закрывает ветки сериализации unit_price/unit_price_rrc когда они None (missing 260-262).
    """
    user = client_api.handler._force_user

    shop = Shop.objects.create(name="NullPriceShop", url="https://n.test", state=True)
    cat = Category.objects.create(name="NullPriceCat")
    product = Product.objects.create(category=cat, name="NullPriceProduct")

    order = Order.objects.create(user=user, status=Order.Status.NEW)
    OrderItem.objects.create(order=order, product=product, shop=shop, quantity=1, unit_price=None, unit_price_rrc=None)

    r = client_api.get("/api/orders/")
    assert r.status_code == 200, r.json()
    body = r.json()
    assert body["Status"] is True
    orders = body["data"]["orders"]
    assert len(orders) == 1
    assert orders[0]["items"][0]["unit_price"] is None
    assert orders[0]["items"][0]["unit_price_rrc"] is None
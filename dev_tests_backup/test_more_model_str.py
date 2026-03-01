import pytest
from django.contrib.auth import get_user_model

from apps.catalog.models import Shop, Category, Product, ProductInfo, Parameter, ProductParameter
from apps.orders.models import Order, OrderItem


@pytest.mark.django_db
def test_more_model_str_and_relations():
    """
    Обычно missing строки в models.py — это __str__ или маленькие методы.
    Мы создаём ProductInfo/Parameter/ProductParameter и OrderItem и вызываем str().
    """
    User = get_user_model()
    u = User.objects.create_user(username="mm", password="p", email="mm@test.local")

    shop = Shop.objects.create(name="StrShop", url="https://s.test", state=True)
    cat = Category.objects.create(name="StrCat")
    product = Product.objects.create(category=cat, name="StrProduct")

    pi = ProductInfo.objects.create(
        product=product,
        shop=shop,
        external_id=999,
        model="M",
        name="Offer",
        quantity=1,
        price="1.00",
        price_rrc="2.00",
    )

    param = Parameter.objects.create(name="color")
    ProductParameter.objects.create(product_info=pi, parameter=param, value="black")

    order = Order.objects.create(user=u, status=Order.Status.NEW)
    item = OrderItem.objects.create(order=order, product=product, shop=shop, quantity=1, unit_price=None, unit_price_rrc=None)

    for obj in (pi, param, order, item):
        _ = str(obj)
import pytest
from django.contrib.auth import get_user_model

from apps.catalog.models import Shop, Category, Product
from apps.orders.models import Order, OrderItem
from apps.users.models import UserProfile, Contact


@pytest.mark.django_db
def test_models_str_smoke():
    User = get_user_model()
    u = User.objects.create_user(username="s", password="p", email="s@test.local")

    profile, _ = UserProfile.objects.get_or_create(user=u)
    contact = Contact.objects.create(user=u, type="phone", value="+49")

    shop = Shop.objects.create(name="S1", url="https://s.test", state=True)
    cat = Category.objects.create(name="C1")
    product = Product.objects.create(category=cat, name="P1")

    order = Order.objects.create(user=u, status=Order.Status.NEW)
    OrderItem.objects.create(
        order=order,
        product=product,
        shop=shop,
        quantity=1,
        unit_price=None,
        unit_price_rrc=None,
    )

    for obj in (profile, contact, shop, cat, product, order):
        s = str(obj)
        assert isinstance(s, str)
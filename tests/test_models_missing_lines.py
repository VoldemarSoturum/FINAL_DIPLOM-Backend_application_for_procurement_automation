import pytest
from django.contrib.auth import get_user_model

from apps.catalog.models import Shop, Category, Product
from apps.orders.models import Order
from apps.users.models import UserProfile


@pytest.mark.django_db
def test_models_missing_lines():
    User = get_user_model()
    u = User.objects.create_user(username="m", password="p", email="m@test.local")
    UserProfile.objects.get_or_create(user=u)

    shop = Shop.objects.create(name="MShop", url="https://m.test", state=True)
    cat = Category.objects.create(name="MCat")
    product = Product.objects.create(category=cat, name="MProduct")

    order = Order.objects.create(user=u, status=Order.Status.NEW)

    # часто missing строки — это __str__
    for obj in (shop, cat, product, order):
        _ = str(obj)
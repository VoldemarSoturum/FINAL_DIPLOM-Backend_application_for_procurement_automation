import pytest
from django.contrib.auth import get_user_model

from apps.catalog.models import (
    Shop, Category, Product, ProductInfo,
    Parameter, ProductParameter
)


@pytest.mark.django_db
def test_catalog_models_str_full():
    shop = Shop.objects.create(name="StrShopX", url="https://x.test", state=True)
    cat = Category.objects.create(name="StrCatX")
    product = Product.objects.create(category=cat, name="StrProductX")

    pi = ProductInfo.objects.create(
        product=product,
        shop=shop,
        external_id=12345,
        model="M",
        name="Offer",
        quantity=1,
        price="1.00",
        price_rrc="2.00",
    )

    param = Parameter.objects.create(name="size")
    pp = ProductParameter.objects.create(product_info=pi, parameter=param, value="XL")

    for obj in (shop, cat, product, pi, param, pp):
        _ = str(obj)
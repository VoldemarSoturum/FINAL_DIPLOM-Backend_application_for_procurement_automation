import pytest
from django.contrib.auth import get_user_model

from apps.catalog.models import Category, Shop, Product, ProductInfo
from apps.users.models import UserProfile


@pytest.fixture()
def client_headers(api_client, db):
    User = get_user_model()
    u = User.objects.create_user(username="client_rem", password="client_pass", email="client_rem@test.local")
    prof, _ = UserProfile.objects.get_or_create(user=u)
    prof.role = UserProfile.Role.CLIENT
    prof.save(update_fields=["role"])

    r = api_client.post("/api/auth/login/", {"username": "client_rem", "password": "client_pass"}, format="json")
    assert r.status_code == 200, r.json()
    token = r.json()["access"]
    return api_client, {"HTTP_AUTHORIZATION": f"Bearer {token}"}


@pytest.mark.django_db
def test_basket_get_creates_basket(client_headers):
    client, headers = client_headers
    r = client.get("/api/basket/", **headers)
    assert r.status_code == 200, r.json()
    body = r.json()
    assert body["Status"] is True
    assert body["data"]["basket"]["status"] == "basket"


@pytest.mark.django_db
def test_checkout_missing_productinfo_branch(client_headers):
    """
    Покрываем ветку: ProductInfo not found for product/shop during checkout.
    Делается так: добавляем item в корзину, затем удаляем ProductInfo.
    """
    client, headers = client_headers

    shop = Shop.objects.create(name="ChkShop", url="https://chk.test", state=True)
    cat = Category.objects.create(name="ChkCat")
    product = Product.objects.create(category=cat, name="ChkProduct")

    pi = ProductInfo.objects.create(
        product=product,
        shop=shop,
        external_id=10,
        model="X",
        name="Offer",
        quantity=5,
        price="10.00",
        price_rrc="12.00",
    )

    r = client.post("/api/basket/items/", {"product_info_id": pi.id, "quantity": 1}, format="json", **headers)
    assert r.status_code == 200, r.json()

    pi.delete()

    r = client.post("/api/basket/checkout/", {}, format="json", **headers)
    assert r.status_code == 409, r.json()
    assert r.json()["Status"] is False
    assert "ProductInfo not found" in str(r.json()["errors"])


@pytest.mark.django_db
def test_checkout_shop_disabled_branch(client_headers):
    """
    Покрываем ветку: shop disabled during checkout.
    """
    client, headers = client_headers

    shop = Shop.objects.create(name="OffShop", url="https://off.test", state=True)
    cat = Category.objects.create(name="OffCat")
    product = Product.objects.create(category=cat, name="OffProduct")

    pi = ProductInfo.objects.create(
        product=product,
        shop=shop,
        external_id=11,
        model="Y",
        name="Offer",
        quantity=5,
        price="10.00",
        price_rrc="12.00",
    )

    r = client.post("/api/basket/items/", {"product_info_id": pi.id, "quantity": 1}, format="json", **headers)
    assert r.status_code == 200, r.json()

    shop.state = False
    shop.save(update_fields=["state"])

    r = client.post("/api/basket/checkout/", {}, format="json", **headers)
    assert r.status_code == 409, r.json()
    assert r.json()["Status"] is False
    assert "disabled" in str(r.json()["errors"]).lower()
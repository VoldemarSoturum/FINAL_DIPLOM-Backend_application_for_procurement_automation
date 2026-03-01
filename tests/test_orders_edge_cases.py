import pytest
from django.contrib.auth import get_user_model

from apps.catalog.models import Category, Shop, Product, ProductInfo
from apps.users.models import UserProfile


@pytest.fixture()
def client_jwt(api_client, db):
    """
    Создаём client пользователя и логинимся по JWT.
    Возвращаем (api_client, headers) где headers содержит Authorization.
    """
    User = get_user_model()
    u = User.objects.create_user(username="client_edge", password="client_pass", email="client_edge@test.local")
    profile, _ = UserProfile.objects.get_or_create(user=u)
    profile.role = UserProfile.Role.CLIENT
    profile.save(update_fields=["role"])

    r = api_client.post("/api/auth/login/", {"username": "client_edge", "password": "client_pass"}, format="json")
    assert r.status_code == 200
    token = r.json()["access"]
    return api_client, {"HTTP_AUTHORIZATION": f"Bearer {token}"}


@pytest.fixture()
def product_setup(db):
    shop_ok = Shop.objects.create(name="ShopOK", url="https://ok.test", state=True)
    shop_off = Shop.objects.create(name="ShopOFF", url="https://off.test", state=False)

    cat = Category.objects.create(name="CatEdge")
    cat.shops.add(shop_ok, shop_off)

    product = Product.objects.create(category=cat, name="EdgePhone")

    pi_ok = ProductInfo.objects.create(
        product=product, shop=shop_ok, external_id=1, model="E1",
        name="Edge offer OK", quantity=2, price="10.00", price_rrc="12.00"
    )
    pi_off = ProductInfo.objects.create(
        product=product, shop=shop_off, external_id=2, model="E2",
        name="Edge offer OFF", quantity=10, price="9.00", price_rrc="11.00"
    )
    pi_zero = ProductInfo.objects.create(
        product=product, shop=shop_ok, external_id=3, model="E3",
        name="Edge offer ZERO", quantity=0, price="8.00", price_rrc="10.00"
    )
    return {"shop_ok": shop_ok, "shop_off": shop_off, "pi_ok": pi_ok, "pi_off": pi_off, "pi_zero": pi_zero}


@pytest.mark.django_db
def test_add_item_productinfo_not_found(client_jwt):
    client, headers = client_jwt
    r = client.post("/api/basket/items/", {"product_info_id": 999999, "quantity": 1}, format="json", **headers)
    assert r.status_code == 404
    body = r.json()
    assert body["Status"] is False


@pytest.mark.django_db
def test_add_item_shop_disabled(client_jwt, product_setup):
    client, headers = client_jwt
    r = client.post("/api/basket/items/", {"product_info_id": product_setup["pi_off"].id, "quantity": 1}, format="json", **headers)
    assert r.status_code == 409
    body = r.json()
    assert body["Status"] is False
    assert "disabled" in str(body["errors"]).lower()


@pytest.mark.django_db
def test_add_item_out_of_stock(client_jwt, product_setup):
    client, headers = client_jwt
    r = client.post("/api/basket/items/", {"product_info_id": product_setup["pi_zero"].id, "quantity": 1}, format="json", **headers)
    assert r.status_code == 409
    body = r.json()
    assert body["Status"] is False
    assert "stock" in str(body["errors"]).lower()


@pytest.mark.django_db
def test_patch_and_delete_item_not_found(client_jwt):
    client, headers = client_jwt
    r = client.patch("/api/basket/items/99999/", {"quantity": 2}, format="json", **headers)
    assert r.status_code == 404
    assert r.json()["Status"] is False

    r = client.delete("/api/basket/items/99999/", format="json", **headers)
    assert r.status_code == 404
    assert r.json()["Status"] is False


@pytest.mark.django_db
def test_checkout_empty_basket(client_jwt):
    client, headers = client_jwt
    r = client.post("/api/basket/checkout/", {}, format="json", **headers)
    assert r.status_code == 409
    body = r.json()
    assert body["Status"] is False
    assert "empty" in str(body["errors"]).lower()


@pytest.mark.django_db
def test_checkout_insufficient_stock(client_jwt, product_setup):
    client, headers = client_jwt

    # add quantity 2 (available)
    r = client.post("/api/basket/items/", {"product_info_id": product_setup["pi_ok"].id, "quantity": 2}, format="json", **headers)
    assert r.status_code == 200

    # reduce stock to 1 before checkout (simulate race / change)
    product_setup["pi_ok"].quantity = 1
    product_setup["pi_ok"].save(update_fields=["quantity"])

    r = client.post("/api/basket/checkout/", {}, format="json", **headers)
    assert r.status_code == 409
    body = r.json()
    assert body["Status"] is False
    assert "not enough" in str(body["errors"]).lower()
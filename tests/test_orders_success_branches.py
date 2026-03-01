import pytest
from django.contrib.auth import get_user_model

from apps.catalog.models import Category, Shop, Product, ProductInfo
from apps.users.models import UserProfile


@pytest.mark.django_db
def test_basket_patch_and_delete_success(api_client):
    User = get_user_model()
    u = User.objects.create_user(username="client_ok", password="pass", email="client_ok@test.local")
    prof, _ = UserProfile.objects.get_or_create(user=u)
    prof.role = UserProfile.Role.CLIENT
    prof.save(update_fields=["role"])

    # login JWT
    r = api_client.post("/api/auth/login/", {"username": "client_ok", "password": "pass"}, format="json")
    token = r.json()["access"]
    headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    shop = Shop.objects.create(name="OkShop", url="https://ok.test", state=True)
    cat = Category.objects.create(name="OkCat")
    product = Product.objects.create(category=cat, name="OkProduct")
    pi = ProductInfo.objects.create(
        product=product, shop=shop, external_id=1, model="OK",
        name="Offer", quantity=10, price="10.00", price_rrc="12.00"
    )

    # add
    r = api_client.post("/api/basket/items/", {"product_info_id": pi.id, "quantity": 1}, format="json", **headers)
    assert r.status_code == 200
    basket = r.json()["data"]["basket"]
    item_id = basket["items"][0]["id"]

    # patch quantity
    r = api_client.patch(f"/api/basket/items/{item_id}/", {"quantity": 3}, format="json", **headers)
    assert r.status_code == 200
    basket = r.json()["data"]["basket"]
    assert basket["items"][0]["quantity"] == 3

    # delete
    r = api_client.delete(f"/api/basket/items/{item_id}/", format="json", **headers)
    assert r.status_code == 200
    basket = r.json()["data"]["basket"]
    assert basket["items"] == []
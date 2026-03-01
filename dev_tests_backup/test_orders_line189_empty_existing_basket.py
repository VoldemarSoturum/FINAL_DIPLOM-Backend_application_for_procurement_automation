import pytest
from apps.orders.models import Order


@pytest.mark.django_db
def test_checkout_empty_existing_basket_hits_line_189(client_api):
    """
    Корзина есть, но items пустые -> попадаем в:
    if not basket.items.exists(): return fail("Basket is empty", 409)  # line 189
    """
    user = client_api.handler._force_user
    Order.objects.get_or_create(user=user, status=Order.Status.BASKET)

    r = client_api.post("/api/basket/checkout/", {}, format="json")
    assert r.status_code == 409, r.json()
    assert r.json()["Status"] is False
import pytest

from apps.orders.models import Order


@pytest.mark.django_db
def test_checkout_items_disappear_inside_transaction(client_api, monkeypatch):
    """
    Имитация race-condition:
    - до транзакции .items.exists() -> True
    - внутри транзакции items пустые -> 409 Basket is empty
    """
    import apps.orders.views as ov

    user = client_api.handler._force_user

    # создаём реальную пустую корзину в БД
    real_basket, _ = Order.objects.get_or_create(user=user, status=Order.Status.BASKET)

    class FakeItems:
        def exists(self):  # проходит внешний чек
            return True

    class FakeBasket:
        id = real_basket.id
        items = FakeItems()

    class FakeQS:
        def first(self):
            return FakeBasket()

    # подменяем _basket_queryset так, чтобы "внешний" basket был фейковым
    monkeypatch.setattr(ov, "_basket_queryset", lambda u: FakeQS())

    # а внутри транзакции будет выбран реальный basket (пустой) -> items пустые
    r = client_api.post("/api/basket/checkout/", {}, format="json")
    assert r.status_code == 409, r.json()
    assert r.json()["Status"] is False
    assert "empty" in str(r.json()["errors"]).lower()
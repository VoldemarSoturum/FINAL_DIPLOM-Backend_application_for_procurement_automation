import pytest
from types import SimpleNamespace

from apps.catalog.models import Shop, Category, Product, ProductInfo
from apps.orders.models import Order


@pytest.mark.django_db
def test_checkout_hits_line202_items_disappear_inside_tx(client_api, monkeypatch, client_user):
    """
    Ловим apps/orders/views.py:202:
    items были (прошли basket.items.exists()), но после select_for_update получили пустые items.
    """
    import apps.orders.views as ov

    shop = Shop.objects.create(name="L202Shop", url="https://l202.test", state=True)
    cat = Category.objects.create(name="L202Cat")
    product = Product.objects.create(category=cat, name="L202Prod")
    pi = ProductInfo.objects.create(
        product=product,
        shop=shop,
        external_id=1,
        model="M",
        name="Offer",
        quantity=10,
        price="10.00",
        price_rrc="12.00",
    )

    r = client_api.post("/api/basket/items/", {"product_info_id": pi.id, "quantity": 1}, format="json")
    assert r.status_code == 200, r.json()

    basket = Order.objects.filter(user=client_user, status=Order.Status.BASKET).first()
    assert basket is not None

    class EmptyItems:
        def all(self):
            return []

    dummy_basket = SimpleNamespace(id=basket.id, items=EmptyItems())

    class DummyQS:
        def filter(self, *a, **k): return self
        def prefetch_related(self, *a, **k): return self
        def first(self): return dummy_basket

    monkeypatch.setattr(ov.Order.objects, "select_for_update", lambda *a, **k: DummyQS())

    r = client_api.post("/api/basket/checkout/", {}, format="json")
    assert r.status_code == 409, r.json()
    assert r.json()["Status"] is False
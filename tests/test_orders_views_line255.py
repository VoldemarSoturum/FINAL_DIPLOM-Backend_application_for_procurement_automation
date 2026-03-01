import pytest

from apps.catalog.models import Shop, Category, Product, ProductInfo


@pytest.mark.django_db
def test_checkout_hits_line255_order_not_found_after_checkout(client_api, monkeypatch):
    """
    Ловим apps/orders/views.py:255:
    после commit order_id есть, но Order.objects.filter(id=order_id).first() -> None
    """
    import apps.orders.views as ov

    shop = Shop.objects.create(name="L255Shop", url="https://l255.test", state=True)
    cat = Category.objects.create(name="L255Cat")
    product = Product.objects.create(category=cat, name="L255Prod")
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

    real_filter = ov.Order.objects.filter

    def filter_wrapper(*args, **kwargs):
        # Только финальный рефетч order по id: Order.objects.filter(id=order_id).first()
        if set(kwargs.keys()) == {"id"}:
            class QS:
                def prefetch_related(self, *a, **k): return self
                def select_related(self, *a, **k): return self
                def first(self): return None
            return QS()
        return real_filter(*args, **kwargs)

    monkeypatch.setattr(ov.Order.objects, "filter", filter_wrapper)

    r = client_api.post("/api/basket/checkout/", {}, format="json")
    assert r.status_code == 500, r.json()
    assert r.json()["Status"] is False
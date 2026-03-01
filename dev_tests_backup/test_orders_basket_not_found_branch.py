import pytest

from apps.catalog.models import Category, Shop, Product, ProductInfo


@pytest.mark.django_db
def test_checkout_basket_not_found_inside_transaction(client_api, monkeypatch):
    """
    Целимся в редкую ветку в BasketCheckoutAPIView:
    внутри transaction select_for_update() возвращает None -> "Basket not found" (404).
    """
    import apps.orders.views as ov

    shop = Shop.objects.create(name="TxShop", url="https://tx.test", state=True)
    cat = Category.objects.create(name="TxCat")
    product = Product.objects.create(category=cat, name="TxProduct")
    pi = ProductInfo.objects.create(
        product=product,
        shop=shop,
        external_id=1,
        model="T",
        name="Offer",
        quantity=10,
        price="10.00",
        price_rrc="12.00",
    )

    # add item so outer checks pass
    r = client_api.post("/api/basket/items/", {"product_info_id": pi.id, "quantity": 1}, format="json")
    assert r.status_code == 200, r.json()

    class DummyQS:
        def filter(self, *args, **kwargs): return self
        def prefetch_related(self, *args, **kwargs): return self
        def first(self): return None

    monkeypatch.setattr(ov.Order.objects, "select_for_update", lambda: DummyQS())

    r = client_api.post("/api/basket/checkout/", {}, format="json")
    assert r.status_code == 404, r.json()
    body = r.json()
    assert body["Status"] is False
    assert "Basket not found" in str(body["errors"])
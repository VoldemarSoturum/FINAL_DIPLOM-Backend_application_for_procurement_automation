import pytest

from apps.catalog.models import Category, Shop, Product, ProductInfo


@pytest.mark.django_db
def test_checkout_email_exception_is_swallowed(client_api, monkeypatch):
    import apps.orders.views as order_views

    # monkeypatch email sender to raise
    monkeypatch.setattr(order_views, "send_order_email_to_customer", lambda order: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(order_views, "send_order_email_to_admin", lambda order: None)

    shop = Shop.objects.create(name="MailShop", url="https://m.test", state=True)
    cat = Category.objects.create(name="MailCat")
    product = Product.objects.create(category=cat, name="MailProduct")
    pi = ProductInfo.objects.create(
        product=product, shop=shop, external_id=1, model="M",
        name="Offer", quantity=10, price="10.00", price_rrc="12.00"
    )

    r = client_api.post("/api/basket/items/", {"product_info_id": pi.id, "quantity": 1}, format="json")
    assert r.status_code == 200, r.json()

    r = client_api.post("/api/basket/checkout/", {}, format="json")
    assert r.status_code == 200, r.json()
    assert r.json()["Status"] is True


@pytest.mark.django_db
def test_checkout_order_none_branch_returns_500(client_api, monkeypatch):
    """
    Покрывает ветку: if order is None -> 500 (Order not found after checkout).
    """
    import apps.orders.views as order_views

    shop = Shop.objects.create(name="NoneShop", url="https://n.test", state=True)
    cat = Category.objects.create(name="NoneCat")
    product = Product.objects.create(category=cat, name="NoneProduct")
    pi = ProductInfo.objects.create(
        product=product, shop=shop, external_id=2, model="N",
        name="Offer", quantity=10, price="10.00", price_rrc="12.00"
    )

    r = client_api.post("/api/basket/items/", {"product_info_id": pi.id, "quantity": 1}, format="json")
    assert r.status_code == 200, r.json()

    # monkeypatch only the "final read" of order after checkout
    real_filter = order_views.Order.objects.filter

    class FakeQS:
        def prefetch_related(self, *args, **kwargs): return self
        def select_related(self, *args, **kwargs): return self
        def first(self): return None

    def fake_filter(*args, **kwargs):
        qs = real_filter(*args, **kwargs)
        # when reading order after checkout we call filter(id=basket.id) -> return fake QS
        if "id" in kwargs and len(kwargs) == 1:
            return FakeQS()
        return qs

    monkeypatch.setattr(order_views.Order.objects, "filter", fake_filter)

    r = client_api.post("/api/basket/checkout/", {}, format="json")
    assert r.status_code == 500, r.json()
    assert r.json()["Status"] is False
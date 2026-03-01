import pytest

from apps.catalog.models import Category, Shop, Product, ProductInfo
from apps.orders.models import Order


@pytest.mark.django_db
def test_checkout_empty_existing_basket_hits_189(client_api):
    user = client_api.handler._force_user
    Order.objects.get_or_create(user=user, status=Order.Status.BASKET)

    r = client_api.post("/api/basket/checkout/", {}, format="json")
    assert r.status_code == 409, r.json()
    assert r.json()["Status"] is False


@pytest.mark.django_db
def test_checkout_email_exception_is_swallowed(client_api, monkeypatch):
    import apps.orders.views as ov

    monkeypatch.setattr(ov, "send_order_email_to_customer", lambda order: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(ov, "send_order_email_to_admin", lambda order: None)

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


@pytest.mark.django_db
def test_checkout_basket_not_found_inside_transaction(client_api, monkeypatch):
    """
    Редкая ветка: внутри transaction select_for_update().first() -> None -> 404 Basket not found.
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
    assert (body.get("Status") is False) or ("detail" in body)
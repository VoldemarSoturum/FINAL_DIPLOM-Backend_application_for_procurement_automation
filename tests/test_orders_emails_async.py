# tests/test_orders_emails_async.py

from types import SimpleNamespace

import pytest
from django.test import override_settings

from apps.catalog.models import Shop, Category, Product, ProductInfo


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=False)
def test_checkout_enqueues_email_task_when_not_eager(
    client_api,
    monkeypatch,
    django_capture_on_commit_callbacks,
):
    import apps.orders.views as ov

    calls = {}

    def fake_delay(order_id, *args, **kwargs):
        calls["order_id"] = order_id
        return SimpleNamespace(id="task-1")

    monkeypatch.setattr(ov.send_order_emails_task, "delay", fake_delay)

    # prepare offer
    shop = Shop.objects.create(name="AsyncShop", url="https://a.test", state=True)
    cat = Category.objects.create(name="AsyncCat")
    product = Product.objects.create(category=cat, name="AsyncProd")
    pi = ProductInfo.objects.create(
        product=product,
        shop=shop,
        external_id=2,
        model="A1",
        name="Offer2",
        quantity=10,
        price="10.00",
        price_rrc="12.00",
    )

    # add
    r = client_api.post("/api/basket/items/", {"product_info_id": pi.id, "quantity": 1}, format="json")
    assert r.status_code == 200, r.json()

    # IMPORTANT: execute on_commit callbacks
    with django_capture_on_commit_callbacks(execute=True):
        r = client_api.post("/api/basket/checkout/", {}, format="json")

    assert r.status_code == 200, r.json()
    body = r.json()

    assert "order_id" in calls
    assert calls["order_id"] == body["data"]["order"]["id"]
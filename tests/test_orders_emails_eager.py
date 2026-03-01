# tests/test_orders_emails_eager.py

import pytest
from django.core import mail
from django.test import override_settings

from apps.catalog.models import Shop, Category, Product, ProductInfo


@pytest.mark.django_db
@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    ADMIN_EMAIL="admin@test.local",
    DEFAULT_FROM_EMAIL="noreply@test.local",
)
def test_checkout_sends_emails_in_eager_mode(client_api, client_user, django_capture_on_commit_callbacks):
    # гарантируем email клиенту
    if not getattr(client_user, "email", ""):
        client_user.email = "client@test.local"
        client_user.save(update_fields=["email"])

    shop = Shop.objects.create(name="MailShop", url="https://m.test", state=True)
    cat = Category.objects.create(name="MailCat")
    product = Product.objects.create(category=cat, name="MailProd")
    pi = ProductInfo.objects.create(
        product=product,
        shop=shop,
        external_id=1,
        model="M1",
        name="Offer",
        quantity=10,
        price="10.00",
        price_rrc="12.00",
    )

    r = client_api.post("/api/basket/items/", {"product_info_id": pi.id, "quantity": 1}, format="json")
    assert r.status_code == 200, r.json()

    mail.outbox.clear()

    # ВАЖНО: выполнить transaction.on_commit callbacks
    with django_capture_on_commit_callbacks(execute=True):
        r = client_api.post("/api/basket/checkout/", {}, format="json")

    assert r.status_code == 200, r.json()
    assert len(mail.outbox) == 2
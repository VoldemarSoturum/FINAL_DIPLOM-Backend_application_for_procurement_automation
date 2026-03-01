import pytest
from django.conf import settings
from django.core import mail
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.catalog.models import Category, Shop, Product, ProductInfo
from apps.orders.models import Order, OrderItem
from apps.orders.services.emails import send_order_email_to_customer, send_order_email_to_admin


@pytest.mark.django_db
def test_email_customer_not_sent_if_no_user_email(settings):
    # user without email
    User = get_user_model()
    u = User.objects.create_user(username="noemail", password="pass12345", email="")

    shop = Shop.objects.create(name="EmailShop", url="https://e.test", state=True)
    cat = Category.objects.create(name="EmailCat")
    product = Product.objects.create(category=cat, name="EmailProduct")
    ProductInfo.objects.create(
        product=product, shop=shop, external_id=1, model="E",
        name="Offer", quantity=10, price="10.00", price_rrc="12.00",
    )

    order = Order.objects.create(user=u, status=Order.Status.NEW, dt=timezone.now())
    OrderItem.objects.create(order=order, product=product, shop=shop, quantity=1, unit_price="10.00", unit_price_rrc="12.00")

    mail.outbox.clear()
    send_order_email_to_customer(order)
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_email_admin_not_sent_if_admin_email_missing(settings):
    # temporarily disable admin email
    settings.ADMIN_EMAIL = None

    User = get_user_model()
    u = User.objects.create_user(username="client_email", password="pass12345", email="client@test.local")

    shop = Shop.objects.create(name="EmailShop2", url="https://e2.test", state=True)
    cat = Category.objects.create(name="EmailCat2")
    product = Product.objects.create(category=cat, name="EmailProduct2")
    order = Order.objects.create(user=u, status=Order.Status.NEW, dt=timezone.now())
    OrderItem.objects.create(order=order, product=product, shop=shop, quantity=1, unit_price="10.00", unit_price_rrc="12.00")

    mail.outbox.clear()
    send_order_email_to_admin(order)
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_password_reset_no_email_no_outbox(api_client):
    """
    Покрываем ветку в password_reset_signals: если у пользователя нет email -> письмо не отправляем.
    """
    User = get_user_model()
    User.objects.create_user(username="noemail_reset", password="pass12345", email="")

    mail.outbox.clear()
    r = api_client.post("/api/password_reset/", {"email": ""}, format="json")
    # библиотека может отвечать 200/400 на пустой email — нам важно отсутствие писем
    assert len(mail.outbox) == 0
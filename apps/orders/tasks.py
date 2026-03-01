# apps/orders/tasks.py
from celery import shared_task
from django.db.models import Prefetch

from apps.orders.models import Order, OrderItem


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def send_order_emails_task(self, order_id: int) -> bool:
    """
    Отправляет письма клиенту и администратору по заказу.
    В тестах выполняется синхронно (CELERY_TASK_ALWAYS_EAGER=True).
    """
    from apps.orders.services.emails import send_order_email_to_admin, send_order_email_to_customer

    order = (
        Order.objects.filter(id=order_id)
        .select_related("user")
        .prefetch_related(Prefetch("items", queryset=OrderItem.objects.select_related("product", "shop")))
        .first()
    )
    if order is None:
        # не ретраим бесконечно, просто считаем выполненным
        return False

    send_order_email_to_customer(order)
    send_order_email_to_admin(order)
    return True
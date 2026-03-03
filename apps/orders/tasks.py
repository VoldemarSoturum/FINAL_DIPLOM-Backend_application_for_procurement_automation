# apps/orders/tasks.py
import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.db.models import Prefetch
from django.utils import timezone

from apps.orders.models import Order, OrderItem
from apps.orders.services.emails import send_order_email_to_admin, send_order_email_to_customer

logger = logging.getLogger(__name__)

_EMAIL_SENT_TTL_SECONDS = 24 * 60 * 60  # 24h


@shared_task(bind=True, name="apps.orders.tasks.send_order_emails_task", max_retries=5)
def send_order_emails_task(self, order_id: int):
    """
    Отправка писем по заказу.

    Idempotency:
    - если письма по order_id уже отправлены — выходим (чтобы ретраи не дубировали)
    Retry:
    - eager (tests/dev): НЕ ретраим, возвращаем Status=False
    - non-eager (worker): self.retry с backoff
    """
    cache_key = f"order:emails:sent:{order_id}"

    # Уже отправляли -> выходим (важно при ретраях)
    if cache.get(cache_key):
        return {"Status": True, "skipped": True}

    order = (
        Order.objects.filter(id=order_id)
        .select_related("user")
        .prefetch_related(Prefetch("items", queryset=OrderItem.objects.select_related("product", "shop")))
        .first()
    )
    if order is None:
        return {"Status": False, "Error": "Order not found"}

    try:
        send_order_email_to_customer(order)
        send_order_email_to_admin(order)
    except Exception as exc:
        logger.exception("send_order_emails_task failed order_id=%s", order_id)

        # ТЕСТЫ / eager: не ретраим, не падаем
        if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
            return {"Status": False, "Error": str(exc)}

        # WORKER: ретраи с backoff (2^retries, но не больше 60s)
        countdown = min(2 ** self.request.retries, 60)
        raise self.retry(exc=exc, countdown=countdown)

    # успех -> ставим флаг, чтобы не дубировать письма при ретраях/повторах
    cache.set(cache_key, True, timeout=_EMAIL_SENT_TTL_SECONDS)
    return {"Status": True}


@shared_task(name="apps.orders.tasks.cleanup_stale_baskets_task")
def cleanup_stale_baskets_task(days: int = 7):
    """
    Периодическая чистка старых корзин (BASKET), чтобы БД не разрасталась.

    По умолчанию: удаляем корзины старше 7 дней.
    """
    cutoff = timezone.now() - timedelta(days=int(days))
    qs = Order.objects.filter(status=Order.Status.BASKET, dt__lt=cutoff)
    deleted_count, _ = qs.delete()
    logger.info("cleanup_stale_baskets_task deleted=%s", deleted_count)
    return deleted_count
# tests/test_orders_tasks_retry_branches.py

import pytest
from django.core.cache import cache
from django.test import override_settings

from apps.catalog.models import Shop, Category, Product
from apps.orders.models import Order, OrderItem


def _run_task(task, *args, **kwargs):
    if hasattr(task, "run"):
        return task.run(*args, **kwargs)
    return task(*args, **kwargs)


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=False)
def test_send_order_emails_task_non_eager_hits_retry_branch(monkeypatch, client_user):
    """
    Закрываем apps/orders/tasks.py: countdown + self.retry(...)
    ВАЖНО:
    - мы запускаем task.run() напрямую (не через worker),
      поэтому celery retry в итоге ре-рейзит исходное исключение (RuntimeError),
      а не celery.exceptions.Retry.
    """
    import apps.orders.tasks as tasks_mod

    cache.clear()

    shop = Shop.objects.create(name="RShop", url="https://r.test", state=True)
    cat = Category.objects.create(name="RCat")
    product = Product.objects.create(category=cat, name="RProd")

    order = Order.objects.create(user=client_user, status=Order.Status.NEW)
    OrderItem.objects.create(
        order=order,
        product=product,
        shop=shop,
        quantity=1,
        unit_price="10.00",
        unit_price_rrc="12.00",
    )

    def boom(_order):
        raise RuntimeError("boom")

    # tasks.py импортирует send_order_email_* на уровне модуля => патчим tasks_mod.*
    monkeypatch.setattr(tasks_mod, "send_order_email_to_customer", boom, raising=True)
    monkeypatch.setattr(tasks_mod, "send_order_email_to_admin", lambda o: None, raising=True)

    with pytest.raises(RuntimeError, match="boom"):
        _run_task(tasks_mod.send_order_emails_task, order.id)
# tests/test_orders_cleanup_task.py

import pytest
from datetime import timedelta
from django.utils import timezone

from apps.orders.models import Order


def _run_task(task, *args, **kwargs):
    if hasattr(task, "run"):
        return task.run(*args, **kwargs)
    return task(*args, **kwargs)


@pytest.mark.django_db
def test_cleanup_stale_baskets_task_cleans_old_and_hits_empty_branch(client_user):
    """
    Цель:
    - создать "очень старую" корзину (должна удалиться)
    - создать свежую корзину (должна остаться)
    - 1-й прогон удаляет старую корзину
    - 2-й прогон удаляет 0 (ветка "нечего чистить")
    """
    import apps.orders.tasks as tasks_mod

    old_dt = timezone.now() - timedelta(days=365)
    fresh_dt = timezone.now()

    old_basket = Order.objects.create(user=client_user, status=Order.Status.BASKET, dt=old_dt)
    fresh_basket = Order.objects.create(user=client_user, status=Order.Status.BASKET, dt=fresh_dt)

    # days=7 по умолчанию => old удалится, fresh останется
    res1 = _run_task(tasks_mod.cleanup_stale_baskets_task)
    assert isinstance(res1, int), res1
    assert res1 >= 1  # обычно 1

    assert not Order.objects.filter(id=old_basket.id).exists()
    assert Order.objects.filter(id=fresh_basket.id).exists()

    # второй прогон: удалять нечего (старых корзин нет)
    res2 = _run_task(tasks_mod.cleanup_stale_baskets_task)
    assert isinstance(res2, int), res2
    assert res2 == 0
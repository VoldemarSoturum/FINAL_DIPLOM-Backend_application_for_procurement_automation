import pytest
from django.test import override_settings
from django.core.cache import cache
from datetime import timedelta
from django.utils import timezone

from apps.orders.models import Order
from apps.orders.tasks import send_order_emails_task, cleanup_stale_baskets_task
from config.celery import app as celery_app


def test_celery_routes_and_queues_are_defined():
    # queues
    qnames = {q.name for q in celery_app.conf.task_queues}
    assert {"default", "imports", "emails"} <= qnames

    # routes
    routes = celery_app.conf.task_routes
    assert routes["apps.partners.tasks.import_price_task"]["queue"] == "imports"
    assert routes["apps.orders.tasks.send_order_emails_task"]["queue"] == "emails"


def test_celery_beat_schedule_defined():
    sched = celery_app.conf.beat_schedule
    assert "cleanup-stale-baskets-nightly" in sched
    assert sched["cleanup-stale-baskets-nightly"]["task"] == "apps.orders.tasks.cleanup_stale_baskets_task"


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_send_order_emails_task_idempotent(monkeypatch, client_user):
    # чистим кеш, чтобы тест был детерминированным
    cache.clear()

    calls = {"customer": 0, "admin": 0}

    # патчим отправку писем в модуле tasks (важно!)
    import apps.orders.tasks as tasks_mod
    monkeypatch.setattr(tasks_mod, "send_order_email_to_customer", lambda order: calls.__setitem__("customer", calls["customer"] + 1))
    monkeypatch.setattr(tasks_mod, "send_order_email_to_admin", lambda order: calls.__setitem__("admin", calls["admin"] + 1))

    order = Order.objects.create(user=client_user, status=Order.Status.NEW)

    r1 = send_order_emails_task.run(order.id)
    assert r1["Status"] is True
    assert calls == {"customer": 1, "admin": 1}

    r2 = send_order_emails_task.run(order.id)
    assert r2["Status"] is True
    assert r2.get("skipped") is True
    assert calls == {"customer": 1, "admin": 1}  # повторно не отправили


@pytest.mark.django_db
def test_cleanup_stale_baskets_task_deletes_only_old_baskets(client_user):
    old_dt = timezone.now() - timedelta(days=10)
    new_dt = timezone.now() - timedelta(days=1)

    old_basket = Order.objects.create(user=client_user, status=Order.Status.BASKET, dt=old_dt)
    new_basket = Order.objects.create(user=client_user, status=Order.Status.BASKET, dt=new_dt)
    other = Order.objects.create(user=client_user, status=Order.Status.NEW, dt=old_dt)

    deleted = cleanup_stale_baskets_task.run(7)
    assert deleted >= 1

    assert not Order.objects.filter(id=old_basket.id).exists()
    assert Order.objects.filter(id=new_basket.id).exists()
    assert Order.objects.filter(id=other.id).exists()
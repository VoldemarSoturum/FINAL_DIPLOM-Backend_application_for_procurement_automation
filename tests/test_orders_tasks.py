# tests/test_orders_tasks.py

import pytest
from celery.exceptions import Retry

from apps.catalog.models import Shop, Category, Product
from apps.orders.models import Order, OrderItem


def _run_task(task, *args, **kwargs):
    # Celery task object has .run, plain function doesn't
    if hasattr(task, "run"):
        return task.run(*args, **kwargs)
    return task(*args, **kwargs)


def _patch_email_sender(monkeypatch, tasks_mod, name: str, fn):
    """
    Если tasks.py импортирует send_order_email_* на уровне модуля — патчим tasks_mod.<name>.
    Если tasks.py импортирует внутри функции — патчим apps.orders.services.emails.<name>.
    """
    if hasattr(tasks_mod, name):
        monkeypatch.setattr(tasks_mod, name, fn, raising=True)
    else:
        import apps.orders.services.emails as emails_mod
        monkeypatch.setattr(emails_mod, name, fn, raising=True)


@pytest.mark.django_db
def test_send_order_emails_task_executes_success_path(monkeypatch, client_user):
    import apps.orders.tasks as tasks_mod

    calls = {"customer": 0, "admin": 0}

    _patch_email_sender(
        monkeypatch,
        tasks_mod,
        "send_order_email_to_customer",
        lambda order: calls.__setitem__("customer", calls["customer"] + 1),
    )
    _patch_email_sender(
        monkeypatch,
        tasks_mod,
        "send_order_email_to_admin",
        lambda order: calls.__setitem__("admin", calls["admin"] + 1),
    )

    shop = Shop.objects.create(name="TShop", url="https://t.test", state=True)
    cat = Category.objects.create(name="TCat")
    product = Product.objects.create(category=cat, name="TProd")

    order = Order.objects.create(user=client_user, status=Order.Status.NEW)
    OrderItem.objects.create(
        order=order,
        product=product,
        shop=shop,
        quantity=1,
        unit_price="10.00",
        unit_price_rrc="12.00",
    )

    _run_task(tasks_mod.send_order_emails_task, order.id)

    assert calls["customer"] == 1
    assert calls["admin"] == 1


@pytest.mark.django_db
def test_send_order_emails_task_order_not_found_branch_does_not_crash():
    import apps.orders.tasks as tasks_mod

    # ветка "order not found" — важно лишь что не падает
    _run_task(tasks_mod.send_order_emails_task, 999999999)


@pytest.mark.django_db
def test_send_order_emails_task_email_exception_branch_is_handled(monkeypatch, client_user):
    """
    Важно:
    - если задача задекорирована autoretry, то при исключении она МОЖЕТ:
      a) поднять Retry/RuntimeError
      b) НЕ поднять исключение (например, retry(throw=False) или внутренняя обработка)
    Наша цель: гарантированно пройти ветку исключения (покрыть строки),
    а не "обязательно упасть".
    """
    import apps.orders.tasks as tasks_mod

    shop = Shop.objects.create(name="EShop", url="https://e.test", state=True)
    cat = Category.objects.create(name="ECat")
    product = Product.objects.create(category=cat, name="EProd")

    order = Order.objects.create(user=client_user, status=Order.Status.NEW)
    OrderItem.objects.create(
        order=order,
        product=product,
        shop=shop,
        quantity=1,
        unit_price="10.00",
        unit_price_rrc="12.00",
    )

    calls = {"customer": 0}

    def boom(_order):
        calls["customer"] += 1
        raise RuntimeError("boom")

    _patch_email_sender(monkeypatch, tasks_mod, "send_order_email_to_customer", boom)
    _patch_email_sender(monkeypatch, tasks_mod, "send_order_email_to_admin", lambda _order: None)

    result = None
    exc = None

    try:
        result = _run_task(tasks_mod.send_order_emails_task, order.id)
    except Exception as e:
        exc = e

    # Главное: ветка с исключением реально дернулась
    assert calls["customer"] >= 1

    # Вариант 1: задача пробросила исключение (часто так при autoretry)
    if exc is not None:
        assert isinstance(exc, (RuntimeError, Retry))
        return

    # Вариант 2: задача обработала исключение внутри и вернула ошибочный результат
    assert isinstance(result, dict), result
    assert result.get("Status") is False, result
# config/celery.py
import os

from celery import Celery
from celery.schedules import crontab
from kombu import Exchange, Queue

# DJANGO_SETTINGS_MODULE уже задаётся в compose/env, но безопасно подстрахуемся
os.environ.setdefault("DJANGO_SETTINGS_MODULE", os.getenv("DJANGO_SETTINGS_MODULE", "config.settings"))

app = Celery("config")

# Подхватываем настройки из Django settings по префиксу CELERY_
app.config_from_object("django.conf:settings", namespace="CELERY")

# Автопоиск tasks.py в apps/*
app.autodiscover_tasks()


# ---------------------------------------------------------------------
# Celery advanced: очереди + роутинг
# ---------------------------------------------------------------------
# 3 очереди:
# - default  : всё обычное
# - imports  : тяжёлое (импорт прайсов)
# - emails   : лёгкое/частое (письма)
default_exchange = Exchange("default", type="direct")
imports_exchange = Exchange("imports", type="direct")
emails_exchange = Exchange("emails", type="direct")

app.conf.task_queues = (
    Queue("default", default_exchange, routing_key="default"),
    Queue("imports", imports_exchange, routing_key="imports"),
    Queue("emails", emails_exchange, routing_key="emails"),
)

app.conf.task_default_queue = "default"
app.conf.task_default_exchange = "default"
app.conf.task_default_exchange_type = "direct"
app.conf.task_default_routing_key = "default"

# Роутинг задач по очередям
app.conf.task_routes = {
    # import price -> imports queue
    "apps.partners.tasks.import_price_task": {"queue": "imports", "routing_key": "imports"},
    # order emails -> emails queue
    "apps.orders.tasks.send_order_emails_task": {"queue": "emails", "routing_key": "emails"},
    # периодическая чистка -> default
    "apps.orders.tasks.cleanup_stale_baskets_task": {"queue": "default", "routing_key": "default"},
}


# ---------------------------------------------------------------------
# Celery advanced: Beat schedule
# ---------------------------------------------------------------------
# Безопасная периодическая задача: чистим "старые корзины" раз в сутки ночью
app.conf.beat_schedule = {
    "cleanup-stale-baskets-nightly": {
        "task": "apps.orders.tasks.cleanup_stale_baskets_task",
        "schedule": crontab(hour=3, minute=0),
        "args": (),
    }
}
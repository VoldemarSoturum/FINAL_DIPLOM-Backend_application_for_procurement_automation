import os
from celery import Celery
from celery.contrib.pytest import celery_app

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

__all__ = ("celery_app",)
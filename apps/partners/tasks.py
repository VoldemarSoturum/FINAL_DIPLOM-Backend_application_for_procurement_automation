# apps/partners/tasks.py
import logging

import requests
from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model

from apps.partners.services.importer import import_price_from_url

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task(bind=True, name="apps.partners.tasks.import_price_task", max_retries=5)
def import_price_task(self, user_id: int, url: str):
    """
    Импорт прайса (тяжёлая задача -> очередь imports).

    Retry:
    - eager (tests/dev): НЕ ретраим, возвращаем Status=False
    - worker: retry только на requests.RequestException
    """
    user = User.objects.filter(id=user_id).first()
    if not user:
        return {"Status": False, "Error": "User not found", "http_status": 400}

    try:
        return import_price_from_url(user=user, url=url)
    except requests.RequestException as exc:
        logger.exception("import_price_task request error url=%s user_id=%s", url, user_id)

        if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
            return {"Status": False, "Error": str(exc), "http_status": 400}

        countdown = min(2 ** self.request.retries, 60)
        raise self.retry(exc=exc, countdown=countdown)
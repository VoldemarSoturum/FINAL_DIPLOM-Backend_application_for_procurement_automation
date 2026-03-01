# apps/partners/tasks.py
from celery import shared_task
from django.contrib.auth import get_user_model

from apps.partners.services.importer import import_price_from_url


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def import_price_task(self, user_id: int, url: str) -> dict:
    """
    Асинхронный импорт прайса поставщика.
    Возвращает dict в unified-формате importer'а.
    """
    User = get_user_model()
    user = User.objects.get(id=user_id)
    return import_price_from_url(user=user, url=url)
import pytest
from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from django.core.cache import cache

from apps.catalog.models import Category


def _count_selects(queries, table_name: str) -> int:
    """
    Считаем только SELECT по конкретной таблице.
    Это делает тест стабильным (транзакции/сейвпоинты не мешают).
    """
    n = 0
    for q in queries:
        sql = q.get("sql", "").upper()
        if "SELECT" in sql and table_name.upper() in sql:
            n += 1
    return n


@pytest.mark.django_db
@override_settings(
    CACHALOT_ENABLED=True,
    CACHALOT_CACHE="default",
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "test-orm-cache",
        }
    },
)
def test_cachalot_caches_second_query():
    cache.clear()

    Category.objects.create(name="Phones")

    # 1) первый вызов — обязан сходить в БД
    with CaptureQueriesContext(connection) as ctx1:
        list(Category.objects.all())
    assert _count_selects(ctx1.captured_queries, "catalog_category") >= 1

    # 2) второй такой же — должен прийти из кеша (0 SELECT в БД)
    with CaptureQueriesContext(connection) as ctx2:
        list(Category.objects.all())
    assert _count_selects(ctx2.captured_queries, "catalog_category") == 0
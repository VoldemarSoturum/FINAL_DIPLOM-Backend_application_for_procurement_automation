# tests/test_throttling.py

import pytest
from django.core.cache import cache
from rest_framework.test import APIRequestFactory
from rest_framework.throttling import AnonRateThrottle

from apps.catalog.views import CategoryListAPIView


class AnonThrottle2PerMin(AnonRateThrottle):
    """
    Жёстко фиксируем rate прямо в throttle классе,
    чтобы тест не зависел от DRF settings cache/reload.
    """
    rate = "2/min"
    scope = "anon"


@pytest.mark.django_db
def test_throttling_anon_rate_limit(monkeypatch):
    """
    Проверяем throttling без флапа:
    - чистим cache
    - подменяем throttle_classes у конкретной view на AnonThrottle2PerMin
    - 3 запроса с одного REMOTE_ADDR => 3-й должен быть 429
    """
    cache.clear()

    monkeypatch.setattr(CategoryListAPIView, "throttle_classes", [AnonThrottle2PerMin], raising=False)

    factory = APIRequestFactory()
    view = CategoryListAPIView.as_view()

    r1 = view(factory.get("/api/catalog/categories/", REMOTE_ADDR="10.0.0.1"))
    r2 = view(factory.get("/api/catalog/categories/", REMOTE_ADDR="10.0.0.1"))
    r3 = view(factory.get("/api/catalog/categories/", REMOTE_ADDR="10.0.0.1"))

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 429
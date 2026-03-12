# tests/test_sentry_debug_endpoint.py

import pytest
from django.test import Client, override_settings


@pytest.mark.django_db
def test_sentry_debug_returns_404_when_debug_false():
    """
    Закрываем ветку:
      if not settings.DEBUG: raise Http404
    """
    with override_settings(DEBUG=False, ROOT_URLCONF="config.urls"):
        c = Client()
        r = c.get("/api/debug/sentry/")
        assert r.status_code == 404


@pytest.mark.django_db
def test_sentry_debug_raises_or_returns_500_when_debug_true():
    """
    Закрываем ветку:
      if settings.DEBUG: 1/0
    В тестах Django иногда ре-рейзит исключение (ZeroDivisionError),
    иногда отдаёт 500 — принимаем оба варианта.
    """
    with override_settings(DEBUG=True, ROOT_URLCONF="config.urls"):
        c = Client()

        try:
            r = c.get("/api/debug/sentry/")
        except ZeroDivisionError:
            # ок: исключение проброшено — строка 1/0 выполнена
            return

        assert r.status_code == 500
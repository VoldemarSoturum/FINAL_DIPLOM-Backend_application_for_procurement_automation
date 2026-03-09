# tests/test_importer_network_retry_passthrough.py

import pytest
import requests


@pytest.mark.django_db
def test_importer_network_error_is_re_raised_for_celery_retry(monkeypatch, supplier_user):
    """
    Stage 9.1 regression test:

    Важно:
    - apps/partners/services/importer.py НЕ должен "съедать" сетевые ошибки.
    - requests.RequestException должен пробрасываться наверх,
      чтобы Celery-task (apps/partners/tasks.py) смог сделать self.retry(...).

    Здесь мы тестируем именно importer.import_price_from_url напрямую.
    """

    import apps.partners.services.importer as importer_mod

    class BoomResponse:
        def raise_for_status(self):
            return None

        @property
        def content(self):
            return b""

    def boom_get(*args, **kwargs):
        raise requests.RequestException("network down")

    monkeypatch.setattr(importer_mod.requests, "get", boom_get, raising=True)

    with pytest.raises(requests.RequestException):
        importer_mod.import_price_from_url(user=supplier_user, url="http://example.test/price.yaml")
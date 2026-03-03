# tests/test_partners_tasks_retry_branches.py

import pytest
import requests
from django.test import override_settings


def _run_task(task, *args, **kwargs):
    if hasattr(task, "run"):
        return task.run(*args, **kwargs)
    return task(*args, **kwargs)


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_import_price_task_request_exception_eager_returns_status_false(monkeypatch, supplier_user):
    """
    Ветка except requests.RequestException при eager=True:
    - должна вернуть {"Status": False, ...}
    """
    import apps.partners.tasks as tasks_mod

    def boom(*args, **kwargs):
        raise requests.RequestException("boom")

    monkeypatch.setattr(tasks_mod, "import_price_from_url", boom, raising=True)

    res = _run_task(tasks_mod.import_price_task, user_id=supplier_user.id, url="http://example.test/x.yaml")
    assert res["Status"] is False
    assert "boom" in res["Error"]


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=False)
def test_import_price_task_request_exception_non_eager_hits_retry_branch(monkeypatch, supplier_user):
    """
    Ветка except requests.RequestException при eager=False:
    - выполняется countdown + raise self.retry(...)
    - при прямом вызове task.run() Celery в итоге ре-рейзит исходный RequestException
    """
    import apps.partners.tasks as tasks_mod

    def boom(*args, **kwargs):
        raise requests.RequestException("boom")

    monkeypatch.setattr(tasks_mod, "import_price_from_url", boom, raising=True)

    with pytest.raises(requests.RequestException, match="boom"):
        _run_task(tasks_mod.import_price_task, user_id=supplier_user.id, url="http://example.test/x.yaml")
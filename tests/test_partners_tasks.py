# tests/test_partners_tasks.py

import pytest


def _run_task(task, *args, **kwargs):
    if hasattr(task, "run"):
        return task.run(*args, **kwargs)
    return task(*args, **kwargs)


@pytest.mark.django_db
def test_import_price_task_calls_importer(monkeypatch, supplier_user):
    import apps.partners.tasks as tasks_mod

    calls = {}

    def fake_import_price_from_url(user, url):
        calls["user_id"] = user.id
        calls["url"] = url
        return {"Status": True}

    monkeypatch.setattr(tasks_mod, "import_price_from_url", fake_import_price_from_url)

    _run_task(tasks_mod.import_price_task, supplier_user.id, "http://example.test/price.yaml")

    assert calls["user_id"] == supplier_user.id
    assert calls["url"] == "http://example.test/price.yaml"
# tests/test_partners_tasks_coverage.py

import pytest
from celery.exceptions import Retry


def _run_task(task, *args, **kwargs):
    # Celery task object has .run, plain function doesn't
    if hasattr(task, "run"):
        return task.run(*args, **kwargs)
    return task(*args, **kwargs)


def _patch_importer(monkeypatch, tasks_mod, fn):
    """
    Если tasks.py импортирует import_price_from_url на уровне модуля — патчим tasks_mod.import_price_from_url.
    Если импорт внутри функции — патчим apps.partners.services.importer.import_price_from_url.
    """
    if hasattr(tasks_mod, "import_price_from_url"):
        monkeypatch.setattr(tasks_mod, "import_price_from_url", fn, raising=True)
    else:
        import apps.partners.services.importer as importer_mod
        monkeypatch.setattr(importer_mod, "import_price_from_url", fn, raising=True)


@pytest.mark.django_db
def test_import_price_task_user_not_found_branch_is_covered(monkeypatch):
    """
    Обычно это строка вида:
    if not user: return {"Status": False, ...}
    (как раз часто попадает на 26 строку).
    """
    import apps.partners.tasks as tasks_mod

    # на всякий случай подменим импортёр, чтобы точно не было реальных запросов
    _patch_importer(monkeypatch, tasks_mod, lambda *a, **k: {"Status": True})

    res = _run_task(tasks_mod.import_price_task, user_id=999999999, url="http://example.test/x.yaml")

    assert isinstance(res, dict), res
    assert res.get("Status") is False, res


@pytest.mark.django_db
def test_import_price_task_success_path_is_covered(monkeypatch, supplier_user):
    """
    Закрываем основную "успешную" ветку (обычно попадает в район 30-37 строк).
    """
    import apps.partners.tasks as tasks_mod

    _patch_importer(monkeypatch, tasks_mod, lambda user, url: {"Status": True, "data": {"ok": True}})

    res = _run_task(tasks_mod.import_price_task, user_id=supplier_user.id, url="http://example.test/price.yaml")

    assert isinstance(res, dict), res
    assert res.get("Status") is True, res


@pytest.mark.django_db
def test_import_price_task_exception_path_is_covered(monkeypatch, supplier_user):
    """
    Закрываем ветку исключения:
    - если task с autoretry -> может поднять Retry/RuntimeError
    - если внутри try/except -> может вернуть {"Status": False, ...}
    Главное: чтобы ветка исключения точно исполнилась.
    """
    import apps.partners.tasks as tasks_mod

    calls = {"n": 0}

    def boom(*args, **kwargs):
        calls["n"] += 1
        raise RuntimeError("boom")

    _patch_importer(monkeypatch, tasks_mod, boom)

    exc = None
    res = None
    try:
        res = _run_task(tasks_mod.import_price_task, user_id=supplier_user.id, url="http://example.test/price.yaml")
    except Exception as e:
        exc = e

    assert calls["n"] >= 1

    if exc is not None:
        assert isinstance(exc, (RuntimeError, Retry))
        return

    assert isinstance(res, dict), res
    assert res.get("Status") is False, res
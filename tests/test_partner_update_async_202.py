import pytest
from types import SimpleNamespace
from django.test import override_settings


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=False)
def test_partner_update_returns_202_and_task_id(supplier_api, monkeypatch):
    import apps.partners.views as pv

    class DummyAsyncResult:
        id = "task-123"

    monkeypatch.setattr(pv.import_price_task, "delay", lambda **kwargs: DummyAsyncResult())

    r = supplier_api.post(
        "/api/partner/update/",
        {"url": "http://example.test/price.yaml"},
        format="json",
    )
    assert r.status_code == 202, r.json()
    body = r.json()
    assert body["Status"] is True
    assert body["data"]["task_id"] == "task-123"


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=False)
def test_partner_update_enqueues_task_with_expected_args(supplier_api, supplier_user, monkeypatch):
    import apps.partners.views as pv

    calls = {}

    def fake_delay(**kwargs):
        calls["kwargs"] = kwargs
        return SimpleNamespace(id="task-999")

    monkeypatch.setattr(pv.import_price_task, "delay", fake_delay)

    url = "http://example.test/price.yaml"
    r = supplier_api.post("/api/partner/update/", {"url": url}, format="json")
    assert r.status_code == 202, r.json()

    assert calls["kwargs"] == {"user_id": supplier_user.id, "url": url}
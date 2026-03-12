# tests/test_importer_yaml_unexpected_exception.py

import pytest

from apps.partners.services.importer import import_price_from_url


class DummyResponse:
    def __init__(self, content: bytes):
        self.content = content

    def raise_for_status(self):
        return None


@pytest.mark.django_db
def test_importer_yaml_unexpected_exception_is_handled(monkeypatch, supplier_user):
    """
    Закрывает ветку "except Exception as e" вокруг yaml.safe_load(...)
    (обычно это как раз 45-46 в coverage).
    """
    import apps.partners.services.importer as importer_mod

    monkeypatch.setattr(importer_mod.requests, "get", lambda url, timeout=20: DummyResponse(b"shop: X"), raising=True)
    monkeypatch.setattr(importer_mod.yaml, "safe_load", lambda content: (_ for _ in ()).throw(RuntimeError("boom")), raising=True)

    res = import_price_from_url(user=supplier_user, url="http://example.test/x.yaml")
    assert res["Status"] is False
    assert "Invalid YAML" in res["Error"]
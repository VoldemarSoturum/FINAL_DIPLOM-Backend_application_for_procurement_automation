import pytest
from types import SimpleNamespace
from unittest.mock import Mock

from apps.catalog.models import Shop


@pytest.mark.django_db
def test_partner_shop_patch_line_274_direct_call(monkeypatch, supplier_user):
    """
    Строка 274 недостижима через HTTP из-за trim_whitespace в DRF CharField.
    Поэтому вызываем PartnerShopAPIView.patch напрямую и подменяем сериализатор,
    чтобы он вернул validated_data с name='   '.
    """
    import apps.partners.views as pv

    # supplier has shop
    Shop.objects.create(name="Line274Shop", url="https://old.test", state=True, user=supplier_user)

    # fake serializer instance
    fake_ser = Mock()
    fake_ser.is_valid.return_value = True
    fake_ser.validated_data = {"name": "   "}  # после strip() станет ""

    # patch serializer class in view module to return our fake serializer
    monkeypatch.setattr(pv, "PartnerShopPatchSerializer", lambda data=None: fake_ser)

    # build minimal request (bypass DRF dispatch)
    req = SimpleNamespace(user=supplier_user, data={"name": "   "})

    resp = pv.PartnerShopAPIView().patch(req)

    assert resp.status_code == 400
    assert resp.data["Status"] is False
    assert "name cannot be empty" in str(resp.data["errors"])
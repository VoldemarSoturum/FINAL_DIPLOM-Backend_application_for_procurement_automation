import pytest
from apps.catalog.models import Shop


@pytest.mark.django_db
def test_partner_shop_patch_no_shop_branch(supplier_api):
    """
    Поставщик без магазина -> PATCH должен вернуть ошибку.
    Это обычно закрывает одну из строк (261).
    """
    r = supplier_api.patch("/api/partner/shop/", {"url": "https://x.test"}, format="json")
    assert r.status_code in (400, 404), r.json()
    assert r.json()["Status"] is False


@pytest.mark.django_db
def test_partner_shop_patch_invalid_serializer_branch(supplier_api, supplier_user):
    """
    Есть shop, но PATCH пустой -> serializer invalid -> fail(serializer.errors)
    Это обычно закрывает вторую строку (274).
    """
    Shop.objects.create(name="PatchLineShop", url="https://p.test", state=True, user=supplier_user)

    r = supplier_api.patch("/api/partner/shop/", {}, format="json")
    assert r.status_code == 400, r.json()
    assert r.json()["Status"] is False
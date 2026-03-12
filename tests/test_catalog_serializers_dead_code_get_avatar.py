# tests/test_catalog_serializers_dead_code_get_avatar.py

import pytest
from types import SimpleNamespace

from apps.catalog.serializers import ProductInfoSerializer


class _Req:
    def build_absolute_uri(self, url: str) -> str:
        return f"http://testserver{url}"


@pytest.mark.django_db
def test_productinfo_serializer_get_avatar_branches():
    ser = ProductInfoSerializer()

    # avatar отсутствует -> None
    obj1 = SimpleNamespace(avatar=None)
    assert ser.get_avatar(obj1) is None

    # avatar есть -> вернёт url (absolute если есть request)
    obj2 = SimpleNamespace(avatar=SimpleNamespace(url="/media/x.png"))
    ser2 = ProductInfoSerializer(context={"request": _Req()})
    assert ser2.get_avatar(obj2) == "http://testserver/media/x.png"
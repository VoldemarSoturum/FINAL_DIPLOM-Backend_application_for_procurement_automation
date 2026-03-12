# tests/test_catalog_tasks.py

import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from apps.catalog.models import Category, Product


def _make_valid_png_bytes() -> bytes:
    """
    Генерим валидный PNG через Pillow — стабильно локально и в Docker.
    """
    from PIL import Image

    buf = io.BytesIO()
    img = Image.new("RGBA", (2, 2), (255, 0, 0, 255))
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.mark.django_db
def test_warm_product_image_renditions_product_not_found():
    import apps.catalog.tasks as tasks_mod

    res = tasks_mod.warm_product_image_renditions(product_id=999999)
    assert res["Status"] is False
    assert "not found" in res["Error"].lower()


@pytest.mark.django_db
def test_warm_product_image_renditions_no_image(tmp_path):
    """
    product есть, image пустой -> Status=False
    """
    import apps.catalog.tasks as tasks_mod

    with override_settings(MEDIA_ROOT=tmp_path, MEDIA_URL="/media/"):
        cat = Category.objects.create(name="Phones")
        product = Product.objects.create(category=cat, name="NoImage")

        res = tasks_mod.warm_product_image_renditions(product_id=product.id)

    assert res["Status"] is False
    assert "not found" in res["Error"].lower()


@pytest.mark.django_db
def test_warm_product_image_renditions_success(monkeypatch, tmp_path):
    """
    Success path:
    - кладём image в MEDIA_ROOT=tmp_path
    - monkeypatch VersatileImageFieldWarmer
    - проверяем warm/clear + корректный ответ
    """
    import apps.catalog.tasks as tasks_mod

    with override_settings(MEDIA_ROOT=tmp_path, MEDIA_URL="/media/"):
        cat = Category.objects.create(name="TV")
        product = Product.objects.create(category=cat, name="WithImage")

        png_bytes = _make_valid_png_bytes()
        product.image = SimpleUploadedFile("product.png", png_bytes, content_type="image/png")
        product.save(update_fields=["image"])

        calls = {"warm": 0, "clear": 0, "args": None}

        class FakeWarmer:
            def __init__(self, instance_or_queryset, rendition_key_set, image_attr):
                calls["args"] = (instance_or_queryset.id, rendition_key_set, image_attr)

            def warm(self):
                calls["warm"] += 1
                return 3, ["fail1"]  # num_created, failed_list

            def clear(self):
                calls["clear"] += 1

        monkeypatch.setattr(tasks_mod, "VersatileImageFieldWarmer", FakeWarmer, raising=True)

        res = tasks_mod.warm_product_image_renditions(product_id=product.id)

    assert res["Status"] is True
    assert res["created"] == 3
    assert res["failed"] == 1
    assert calls["warm"] == 1
    assert calls["clear"] == 1
    assert calls["args"][0] == product.id
    assert calls["args"][1] == "product"
    assert calls["args"][2] == "image"
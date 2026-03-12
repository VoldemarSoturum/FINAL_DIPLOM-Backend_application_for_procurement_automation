# tests/test_product_image_upload.py

import pytest
from io import BytesIO

from django.test import override_settings
from django.core.files.uploadedfile import SimpleUploadedFile

from PIL import Image

from apps.catalog.models import Category, Product


@pytest.mark.django_db
def test_product_image_upload_patch_multipart(api_client, tmp_path):
    """
    PATCH /api/catalog/products/{id}/image/ (multipart)
    Стабильно локально и в Docker: генерим валидный PNG через Pillow.
    """
    with override_settings(MEDIA_ROOT=tmp_path):
        cat = Category.objects.create(name="Phones")
        product = Product.objects.create(category=cat, name="iPhone 15")

        buf = BytesIO()
        Image.new("RGB", (1, 1)).save(buf, format="PNG")
        upload = SimpleUploadedFile("test.png", buf.getvalue(), content_type="image/png")

        r = api_client.patch(
            f"/api/catalog/products/{product.id}/image/",
            data={"image": upload},
            format="multipart",
        )

        assert r.status_code == 200, r.json()
        body = r.json()
        assert body.get("image"), body

        product.refresh_from_db()
        assert product.image.name

        # файл реально записался в MEDIA_ROOT
        saved_path = tmp_path / product.image.name
        assert saved_path.exists()
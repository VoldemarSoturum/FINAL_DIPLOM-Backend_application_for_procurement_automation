import pytest
from django.test import override_settings
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.catalog.models import Category, Product


@pytest.mark.django_db
def test_product_image_upload_patch_multipart(api_client, tmp_path):
    """
    PATCH /api/catalog/products/{id}/image/ (multipart)

    Почему так:
    - tmp_path (pytest) + override_settings(MEDIA_ROOT=tmp_path) => тест не пачкает проект
    - SimpleUploadedFile => стабильный "файл" без реальных картинок
    - format="multipart" => DRF сам выставит правильный Content-Type
    """
    with override_settings(MEDIA_ROOT=tmp_path):
        cat = Category.objects.create(name="Phones")
        product = Product.objects.create(category=cat, name="iPhone 15")

        # Минимальные валидные bytes для png. Этого достаточно для ImageField в большинстве окружений.
        # Если Pillow будет ругаться (редко), зам на реальный маленький png-файл.
        png_bytes = (
            b"\x89PNG\r\n\x1a\n"
            b"\x00\x00\x00\rIHDR"
            b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
            b"\x1f\x15\xc4\x89"
            b"\x00\x00\x00\nIDATx\x9cc`\x00\x00\x00\x02\x00\x01"
            b"\xe2!\xbc3"
            b"\x00\x00\x00\x00IEND\xaeB`\x82"
        )

        upload = SimpleUploadedFile(
            name="test.png",
            content=png_bytes,
            content_type="image/png",
        )

        url = f"/api/catalog/products/{product.id}/image/"
        r = api_client.patch(url, data={"image": upload}, format="multipart")

        assert r.status_code == 200, r.json()

        body = r.json()
        assert body.get("id") == product.id
        assert "image" in body
        assert body["image"], body  # должна быть непустая строка/URL

        product.refresh_from_db()
        assert product.image, "image field must be saved on model"
        assert product.image.name.startswith("products/"), product.image.name
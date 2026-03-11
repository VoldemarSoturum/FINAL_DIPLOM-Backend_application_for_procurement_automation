from __future__ import annotations

from rest_framework import serializers

from apps.catalog.models import Category, Shop, Product, ProductInfo, ProductParameter


class CategorySerializer(serializers.ModelSerializer):
    """
    Плоский сериализатор категории.
    Используется в списках и вложенно в ProductSerializer.
    """
    class Meta:
        model = Category
        fields = ("id", "name")


class ShopSerializer(serializers.ModelSerializer):
    """
    Сериализатор магазина (поставщика).
    Возвращаем state, чтобы клиент UI понимал: принимает ли поставщик заказы.
    """
    class Meta:
        model = Shop
        fields = ("id", "name", "url", "state")


class ProductParameterSerializer(serializers.ModelSerializer):
    """
    Параметры оффера (ProductInfo -> parameters -> Parameter).
    В API отдаём имя параметра строкой (parameter.name), чтобы не тащить отдельные id.
    """
    parameter = serializers.CharField(source="parameter.name")

    class Meta:
        model = ProductParameter
        fields = ("parameter", "value")


class ProductInfoSerializer(serializers.ModelSerializer):
    """
    Оффер (предложение) товара у конкретного магазина.
    - shop вложенно (чтобы сразу видеть магазин)
    - parameters вложенно (чтобы не делать доп. запросов)
    """
    shop = ShopSerializer(read_only=True)
    parameters = ProductParameterSerializer(many=True, read_only=True)

    class Meta:
        model = ProductInfo
        fields = (
            "id",
            "external_id",
            "model",
            "name",
            "quantity",
            "price",
            "price_rrc",
            "shop",
            "parameters",
        )

    def get_avatar(self, obj):
        if not getattr(obj, "avatar", None):
            return None
        request = self.context.get("request")
        url = obj.avatar.url
        return request.build_absolute_uri(url) if request else url

class ProductSerializer(serializers.ModelSerializer):
    """
    Основной сериализатор продукта:
    - category: вложенная категория (read-only)
    - offers: офферы (ProductInfo), подтягиваются через related_name="product_infos"
    - image: ссылка на картинку продукта (если загружена)
    """
    category = CategorySerializer(read_only=True)

    # "offers" в API, но источник данных в модели: product_infos
    offers = ProductInfoSerializer(source="product_infos", many=True, read_only=True)

    # Возвращаем URL изображения продукта.
    # DRF корректно соберёт абсолютный URL, если request есть в serializer context.
    image = serializers.ImageField(read_only=True, required=False, allow_null=True)

    class Meta:
        model = Product
        fields = ("id", "name", "category", "offers", "image")


class ProductImageUploadSerializer(serializers.Serializer):
    """
    Upload-сериализатор для multipart PATCH:
      PATCH /api/catalog/products/{id}/image/
      Content-Type: multipart/form-data
      form-data:
        - image: <file>

    Он НЕ описывает Product целиком — только входящий файл.
    """
    image = serializers.ImageField(required=True)
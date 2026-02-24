from rest_framework import serializers

from apps.catalog.models import Category, Shop, Product, ProductInfo, ProductParameter


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name")


class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ("id", "name", "url", "state")


class ProductParameterSerializer(serializers.ModelSerializer):
    parameter = serializers.CharField(source="parameter.name")

    class Meta:
        model = ProductParameter
        fields = ("parameter", "value")


class ProductInfoSerializer(serializers.ModelSerializer):
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


class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    offers = ProductInfoSerializer(source="product_infos", many=True, read_only=True)

    class Meta:
        model = Product
        fields = ("id", "name", "category", "offers")
from rest_framework import serializers

from apps.orders.models import Order, OrderItem


class BasketItemAddSerializer(serializers.Serializer):
    product_info_id = serializers.IntegerField(required=True)
    quantity = serializers.IntegerField(min_value=1, required=True)


class BasketItemUpdateSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1, required=True)


class BasketItemSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(source="product.id", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    shop_id = serializers.IntegerField(source="shop.id", read_only=True)
    shop_name = serializers.CharField(source="shop.name", read_only=True)

    class Meta:
        model = OrderItem
        fields = (
            "id",
            "product_id",
            "product_name",
            "shop_id",
            "shop_name",
            "quantity",
            "unit_price",
            "unit_price_rrc",
        )


class BasketSerializer(serializers.ModelSerializer):
    items = BasketItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ("id", "status", "dt", "items")

class OrderListItemSerializer(serializers.ModelSerializer):
    items = BasketItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ("id", "status", "dt", "items")
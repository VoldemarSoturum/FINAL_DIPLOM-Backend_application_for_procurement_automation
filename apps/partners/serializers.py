from rest_framework import serializers


class PartnerUpdateSerializer(serializers.Serializer):
    url = serializers.URLField(required=True)


class PartnerStateSerializer(serializers.Serializer):
    state = serializers.BooleanField(required=True)


class PartnerShopCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=True)
    url = serializers.URLField(required=False, allow_blank=True)


class PartnerShopPatchSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False, allow_blank=False)
    url = serializers.URLField(required=False, allow_blank=True)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Provide at least one field: name or url")
        return attrs


class UnifiedResponseSerializer(serializers.Serializer):
    Status = serializers.BooleanField()
    data = serializers.DictField(required=False, allow_null=True)
    errors = serializers.JSONField(required=False, allow_null=True)




class PartnerOrderItemOutSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    product_id = serializers.IntegerField()
    product_name = serializers.CharField()
    quantity = serializers.IntegerField()
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    unit_price_rrc = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    total = serializers.DecimalField(max_digits=14, decimal_places=2, required=False, allow_null=True)


class PartnerOrderOutSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    dt = serializers.DateTimeField()
    status = serializers.CharField()
    customer = serializers.DictField()
    items = PartnerOrderItemOutSerializer(many=True)


class PartnerOrdersDataOutSerializer(serializers.Serializer):
    orders = PartnerOrderOutSerializer(many=True)
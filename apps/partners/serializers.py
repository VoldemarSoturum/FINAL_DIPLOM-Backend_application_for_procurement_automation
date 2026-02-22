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
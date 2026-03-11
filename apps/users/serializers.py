from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import UserProfile, Contact

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ("id", "username", "email", "password")

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserPublicSerializer(serializers.ModelSerializer):
    """
    Публичная информация о пользователе (удобно вкладывать в профиль/ответы).
    """
    class Meta:
        model = User
        fields = ("id", "username", "email")
        read_only_fields = fields


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ("id", "type", "value", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Полноценный сериализатор профиля:
    - user: вложенный объект (id/username/email)
    - role: роль пользователя
    - contacts: список контактов (работает и при related_name='contacts', и при дефолтном contact_set)
    - created_at/updated_at
    """
    user = UserPublicSerializer(read_only=True)
    contacts = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = (
            "id",
            "user",
            "role",
            "avatar",
            "contacts",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "user", "contacts", "created_at", "updated_at")

    def get_contacts(self, obj: UserProfile):
        """
        Не привязываемся к related_name.
        Варианты:
        - user.contacts (если related_name="contacts")
        - user.contact_set (если related_name не задан)
        """
        user = getattr(obj, "user", None)
        if user is None:
            return []

        # related_name="contacts"
        if hasattr(user, "contacts"):
            qs = user.contacts.all()
            return ContactSerializer(qs, many=True).data

        # default related name
        if hasattr(user, "contact_set"):
            qs = user.contact_set.all()
            return ContactSerializer(qs, many=True).data

        return []
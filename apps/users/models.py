from django.db import models
from django.conf import settings
from django.db import models
from django.utils import timezone


class UserProfile(models.Model):
    class Role(models.TextChoices):
        CLIENT = "client", "Client"
        SUPPLIER = "supplier", "Supplier"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CLIENT)

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.user} ({self.role})"


class Contact(models.Model):
    class ContactType(models.TextChoices):
        EMAIL = "email", "Email"
        PHONE = "phone", "Phone"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="contacts",
    )
    type = models.CharField(max_length=20, choices=ContactType.choices)
    value = models.CharField(max_length=255)

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "type", "value"], name="uniq_user_contact"),
        ]
        indexes = [
            models.Index(fields=["user", "type"]),
        ]

    def __str__(self) -> str:
        return f"{self.user}: {self.type}={self.value}"

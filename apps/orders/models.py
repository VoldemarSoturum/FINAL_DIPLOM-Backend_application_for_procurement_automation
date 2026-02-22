# Create your models here.
from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.catalog.models import Product, Shop


class Order(models.Model):
    class Status(models.TextChoices):
        BASKET = "basket", "Basket"
        NEW = "new", "New"
        CONFIRMED = "confirmed", "Confirmed"
        PROCESSING = "processing", "Processing"
        DONE = "done", "Done"
        CANCELED = "canceled", "Canceled"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders")
    dt = models.DateTimeField(default=timezone.now, editable=False)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.BASKET)

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["dt"]),
        ]

    def __str__(self) -> str:
        return f"Order#{self.id} {self.user} {self.status}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="order_items")
    shop = models.ForeignKey(Shop, on_delete=models.PROTECT, related_name="order_items")
    quantity = models.PositiveIntegerField(default=1)

    # Важное дополнение: фиксация цены на момент заказа (для накладных/писем)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    unit_price_rrc = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["order", "product", "shop"], name="uniq_order_item_position"),
        ]
        indexes = [
            models.Index(fields=["order"]),
            models.Index(fields=["shop"]),
        ]

    def __str__(self) -> str:
        return f"{self.order_id}: {self.product} x{self.quantity}"
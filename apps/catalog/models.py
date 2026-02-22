from django.db import models

# Create your models here.
from django.db import models
from django.utils import timezone


class Shop(models.Model):
    name = models.CharField(max_length=255, unique=True)
    url = models.URLField(max_length=500, blank=True)
    state = models.BooleanField(default=True, help_text="Принимает ли поставщик заказы")

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)
    shops = models.ManyToManyField(Shop, related_name="categories", blank=True)

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    name = models.CharField(max_length=255)

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["category", "name"], name="uniq_product_in_category"),
        ]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["category"]),
        ]

    def __str__(self) -> str:
        return self.name


class ProductInfo(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="product_infos")
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="product_infos")

    name = models.CharField(max_length=255, help_text="Название позиции у поставщика")
    quantity = models.PositiveIntegerField(default=0)

    price = models.DecimalField(max_digits=12, decimal_places=2)
    price_rrc = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["product", "shop"], name="uniq_product_shop_info"),
        ]
        indexes = [
            models.Index(fields=["shop"]),
            models.Index(fields=["product"]),
        ]

    def __str__(self) -> str:
        return f"{self.product} @ {self.shop}"
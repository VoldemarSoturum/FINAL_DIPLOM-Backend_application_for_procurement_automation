from django.conf import settings
from django.db import models
from django.utils import timezone


class Shop(models.Model):
    name = models.CharField(max_length=255, unique=True)
    url = models.URLField(max_length=500, blank=True)

    # Владелец магазина/поставщик (важно для импорта и API партнёра)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="shop",
    )

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

    # Поля из YAML-прайса (goods[].id / goods[].model)
    external_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    model = models.CharField(max_length=80, blank=True)

    name = models.CharField(max_length=255, help_text="Название позиции у поставщика")
    quantity = models.PositiveIntegerField(default=0)

    price = models.DecimalField(max_digits=12, decimal_places=2)
    price_rrc = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            # Для импорта обновляем прайс по (shop, external_id)
            models.UniqueConstraint(fields=["shop", "external_id"], name="uniq_shop_external_id"),
        ]
        indexes = [
            models.Index(fields=["shop"]),
            models.Index(fields=["product"]),
        ]

    def __str__(self) -> str:
        return f"{self.product} @ {self.shop}"


class Parameter(models.Model):
    name = models.CharField(max_length=255, unique=True)

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name


class ProductParameter(models.Model):
    product_info = models.ForeignKey(ProductInfo, on_delete=models.CASCADE, related_name="parameters")
    parameter = models.ForeignKey(Parameter, on_delete=models.CASCADE, related_name="product_parameters")
    value = models.CharField(max_length=255)

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["product_info", "parameter"], name="uniq_productinfo_parameter"),
        ]
        indexes = [
            models.Index(fields=["parameter"]),
        ]

    def __str__(self) -> str:
        return f"{self.product_info}: {self.parameter}={self.value}"
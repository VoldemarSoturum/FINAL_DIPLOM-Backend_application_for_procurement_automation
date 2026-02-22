from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Shop, Category, Product, ProductInfo, Parameter, ProductParameter


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "state", "url", "created_at")
    list_filter = ("state",)
    search_fields = ("name", "url")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)
    filter_horizontal = ("shops",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "category")
    list_filter = ("category",)
    search_fields = ("name",)


@admin.register(ProductInfo)
class ProductInfoAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "shop", "name", "quantity", "price", "price_rrc")
    list_filter = ("shop",)
    search_fields = ("product__name", "name", "shop__name")

@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(ProductParameter)
class ProductParameterAdmin(admin.ModelAdmin):
    list_display = ("id", "product_info", "parameter", "value")
    list_filter = ("parameter",)
    search_fields = ("product_info__product__name", "value", "parameter__name")
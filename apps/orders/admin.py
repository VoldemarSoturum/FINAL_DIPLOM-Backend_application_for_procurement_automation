# Register your models here.
from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "dt", "created_at", "updated_at")
    list_filter = ("status",)
    search_fields = ("user__username", "user__email")
    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "product", "shop", "quantity", "unit_price")
    list_filter = ("shop",)
    search_fields = ("product__name", "shop__name")
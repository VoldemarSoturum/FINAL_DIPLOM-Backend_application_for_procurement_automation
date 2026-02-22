from django.contrib import admin

# Register your models here.

from django.contrib import admin
from .models import UserProfile, Contact


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "role", "created_at", "updated_at")
    list_filter = ("role",)
    search_fields = ("user__username", "user__email")


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "type", "value", "created_at")
    list_filter = ("type",)
    search_fields = ("user__username", "user__email", "value")
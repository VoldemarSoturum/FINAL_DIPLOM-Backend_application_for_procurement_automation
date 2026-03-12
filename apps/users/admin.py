# apps/users/admin.py

from __future__ import annotations

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import Contact, UserProfile

User = get_user_model()


class UserProfileInline(admin.StackedInline):
    """
    Профиль пользователя редактируется прямо в карточке User.
    """
    model = UserProfile
    can_delete = False
    extra = 0


class UserAdmin(DjangoUserAdmin):
    """
    Расширяем стандартную админку Django User:
    - добавляем inline UserProfile
    - показываем роль в списке пользователей
    """
    inlines = [UserProfileInline]
    list_select_related = ("profile",)
    list_display = DjangoUserAdmin.list_display + ("get_role",)

    @admin.display(description="Role", ordering="profile__role")
    def get_role(self, obj):
        return getattr(getattr(obj, "profile", None), "role", "-")


# -----------------------------
# Safe re-register User admin
# -----------------------------
# Важно: импорт django.contrib.auth.admin сам регистрирует User.
# Поэтому мы гарантированно удаляем регистрацию и ставим свою.
try:
    if admin.site.is_registered(User):
        admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass

admin.site.register(User, UserAdmin)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "role", "created_at", "updated_at")
    list_select_related = ("user",)


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "type", "value", "created_at")
    list_filter = ("type",)
    search_fields = ("user__username", "user__email", "value")
    list_select_related = ("user",)
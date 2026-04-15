from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from expenses.services.balance import get_balance
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "full_name", "is_admin", "is_active", "balance_display")
    list_filter = ("is_admin", "is_active")
    search_fields = ("username", "full_name")
    ordering = ("username",)
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Профиль", {"fields": ("full_name",)}),
        ("Права", {"fields": ("is_active", "is_admin", "is_staff", "is_superuser")}),
        ("Telegram", {"fields": ("telegram_id", "telegram_link_code")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("username", "full_name", "password1", "password2")}),
    )

    def balance_display(self, obj):
        return f"{get_balance(obj)} ₸"
    balance_display.short_description = "Баланс"

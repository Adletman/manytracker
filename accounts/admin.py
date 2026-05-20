from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.urls import path
from django.utils.html import format_html

from expenses.services.balance import get_balance
from .admin_views import generate_telegram_code
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "username", "full_name", "is_admin", "is_active",
        "balance_display", "telegram_status", "telegram_action",
    )
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

    class Media:
        js = ("admin/js/telegram_code.js",)

    def balance_display(self, obj):
        return f"{get_balance(obj)} ₸"
    balance_display.short_description = "Баланс"

    def telegram_status(self, obj):
        if obj.telegram_id:
            return format_html('<span style="color:green">привязан</span>')
        return "—"
    telegram_status.short_description = "TG"

    def telegram_action(self, obj):
        if obj.telegram_id:
            return "—"
        return format_html(
            '<button type="button" class="btn-gen-tg-code" data-user-id="{}">Сген. код</button>',
            obj.id,
        )
    telegram_action.short_description = "TG-код"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<int:user_id>/gen-tg-code/",
                self.admin_site.admin_view(generate_telegram_code),
                name="accounts_user_gen_tg_code",
            ),
        ]
        return custom + urls

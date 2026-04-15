import csv
from django.contrib import admin
from django.http import HttpResponse

from .models import ExpenseCategory, Topup, Expense, ExpenseAttachment, AuditLog


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "sort_order")
    list_editable = ("is_active", "sort_order")
    search_fields = ("name",)


@admin.register(Topup)
class TopupAdmin(admin.ModelAdmin):
    list_display = ("date", "user", "amount", "comment", "created_by", "created_at")
    list_filter = ("user", "date")
    search_fields = ("comment",)
    date_hierarchy = "date"

    def save_model(self, request, obj, form, change):
        if not change and not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


class ExpenseAttachmentInline(admin.TabularInline):
    model = ExpenseAttachment
    extra = 0
    readonly_fields = ("original_name", "mime_type", "size", "uploaded_at")


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = (
        "date", "user", "category", "custom_category_name",
        "amount", "comment_short", "created_via", "is_deleted", "created_at",
    )
    list_filter = ("user", "category", "created_via", "is_deleted", "date")
    search_fields = ("comment", "custom_category_name")
    date_hierarchy = "date"
    inlines = [ExpenseAttachmentInline]
    actions = ["export_as_csv"]

    def comment_short(self, obj):
        return (obj.comment or "")[:40]
    comment_short.short_description = "Комментарий"

    def export_as_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="expenses.csv"'
        writer = csv.writer(response)
        writer.writerow(["Дата", "Сотрудник", "Категория", "Сумма", "Комментарий", "Источник"])
        for e in queryset.select_related("user", "category"):
            writer.writerow([
                e.date, e.user.username,
                e.category.name if e.category else e.custom_category_name,
                e.amount, e.comment, e.created_via,
            ])
        return response
    export_as_csv.short_description = "Экспорт в CSV"


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "action", "entity", "entity_id")
    list_filter = ("action", "entity", "user")
    readonly_fields = ("user", "action", "entity", "entity_id", "diff", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

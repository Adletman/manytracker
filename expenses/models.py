from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class ExpenseCategory(models.Model):
    name = models.CharField(max_length=64, unique=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class Topup(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="topups",
    )
    amount = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    date = models.DateField()
    comment = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_topups",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"+{self.amount} ₸ → {self.user} ({self.date})"


class Expense(models.Model):
    CREATED_VIA_WEB = "web"
    CREATED_VIA_TELEGRAM = "telegram"
    CREATED_VIA_CHOICES = [
        (CREATED_VIA_WEB, "Веб"),
        (CREATED_VIA_TELEGRAM, "Telegram"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="expenses",
    )
    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="expenses",
    )
    custom_category_name = models.CharField(max_length=64, blank=True)
    amount = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    date = models.DateField()
    comment = models.TextField(blank=True)
    created_via = models.CharField(
        max_length=16, choices=CREATED_VIA_CHOICES, default=CREATED_VIA_WEB,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ["-date", "-created_at"]
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(category__isnull=False, custom_category_name="")
                    | models.Q(category__isnull=True) & ~models.Q(custom_category_name="")
                ),
                name="category_xor_custom",
            ),
        ]

    def category_display(self):
        return self.category.name if self.category else self.custom_category_name

    def __str__(self):
        return f"-{self.amount} ₸ {self.category_display()} ({self.user})"

from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from expenses.models import Expense, AuditLog
from expenses.services.audit import write_audit
from expenses.services.balance import get_balance


EDIT_WINDOW = timedelta(hours=24)


class NegativeBalanceError(Exception):
    def __init__(self, projected_balance: Decimal):
        self.projected_balance = projected_balance
        super().__init__(f"Баланс станет {projected_balance} ₸")


class EditWindowExpiredError(Exception):
    pass


def _can_edit(actor, expense) -> bool:
    if getattr(actor, "is_admin", False):
        return True
    if actor.id != expense.user_id:
        return False
    age = timezone.now() - expense.created_at
    return age <= EDIT_WINDOW


def create_expense(
    *,
    user,
    category,
    custom_name: str,
    amount: Decimal,
    expense_date,
    comment: str,
    created_via: str,
    allow_negative: bool = False,
):
    if amount <= 0:
        raise ValueError("Сумма должна быть больше нуля")
    if (category is None) == (custom_name == ""):
        raise ValueError("Укажите либо категорию, либо своё название")

    projected = get_balance(user) - amount
    if projected < 0 and not allow_negative:
        raise NegativeBalanceError(projected)

    with transaction.atomic():
        expense = Expense.objects.create(
            user=user,
            category=category,
            custom_category_name=custom_name,
            amount=amount,
            date=expense_date,
            comment=comment,
            created_via=created_via,
        )
        write_audit(
            user=user,
            action=AuditLog.ACTION_CREATE,
            entity=AuditLog.ENTITY_EXPENSE,
            entity_id=expense.id,
            diff={
                "amount": str(amount),
                "date": expense_date.isoformat(),
                "category_id": category.id if category else None,
                "custom_name": custom_name,
            },
        )
    return expense


def update_expense(*, actor, expense, category, custom_name, amount, expense_date, comment):
    if not _can_edit(actor, expense):
        raise EditWindowExpiredError("Редактирование недоступно (прошло больше 24 часов)")
    if amount <= 0:
        raise ValueError("Сумма должна быть больше нуля")
    if (category is None) == (custom_name == ""):
        raise ValueError("Укажите либо категорию, либо своё название")

    before = {
        "amount": str(expense.amount),
        "comment": expense.comment,
        "category_id": expense.category_id,
        "custom_name": expense.custom_category_name,
        "date": expense.date.isoformat(),
    }

    with transaction.atomic():
        expense.category = category
        expense.custom_category_name = custom_name
        expense.amount = amount
        expense.date = expense_date
        expense.comment = comment
        expense.save()
        write_audit(
            user=actor,
            action=AuditLog.ACTION_UPDATE,
            entity=AuditLog.ENTITY_EXPENSE,
            entity_id=expense.id,
            diff={
                "before": before,
                "after": {
                    "amount": str(amount),
                    "comment": comment,
                    "category_id": category.id if category else None,
                    "custom_name": custom_name,
                    "date": expense_date.isoformat(),
                },
            },
        )
    return expense


def delete_expense(*, actor, expense):
    if not _can_edit(actor, expense):
        raise EditWindowExpiredError("Удаление недоступно (прошло больше 24 часов)")
    with transaction.atomic():
        expense.is_deleted = True
        expense.save(update_fields=["is_deleted", "updated_at"])
        write_audit(
            user=actor,
            action=AuditLog.ACTION_DELETE,
            entity=AuditLog.ENTITY_EXPENSE,
            entity_id=expense.id,
            diff={"amount": str(expense.amount)},
        )

from decimal import Decimal
from django.db.models import Sum
from expenses.models import Topup, Expense


def get_balance(user) -> Decimal:
    topups_sum = Topup.objects.filter(user=user).aggregate(s=Sum("amount"))["s"] or Decimal("0.00")
    expenses_sum = (
        Expense.objects.filter(user=user, is_deleted=False)
        .aggregate(s=Sum("amount"))["s"] or Decimal("0.00")
    )
    return topups_sum - expenses_sum

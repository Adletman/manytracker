from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from expenses.models import Expense, Topup
from expenses.services.balance import get_balance


@login_required
def cabinet(request):
    balance = get_balance(request.user)
    recent_expenses = Expense.objects.filter(
        user=request.user, is_deleted=False
    ).select_related("category")[:10]
    recent_topups = Topup.objects.filter(user=request.user)[:5]
    return render(request, "expenses/cabinet.html", {
        "balance": balance,
        "recent_expenses": recent_expenses,
        "recent_topups": recent_topups,
    })

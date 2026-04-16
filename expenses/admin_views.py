from datetime import date
from decimal import Decimal
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum
from django.shortcuts import render
from django.contrib.auth import get_user_model
from expenses.models import Expense, Topup
from expenses.services.balance import get_balance

User = get_user_model()


@staff_member_required
def dashboard(request):
    today = date.today()
    date_from = request.GET.get("from", today.replace(day=1).isoformat())
    date_to = request.GET.get("to", today.isoformat())

    users = User.objects.filter(is_active=True, is_admin=False).order_by("full_name", "username")
    user_balances = []
    for u in users:
        bal = get_balance(u)
        user_balances.append({"user": u, "balance": bal})

    expenses_qs = Expense.objects.filter(is_deleted=False, date__gte=date_from, date__lte=date_to)
    total_expenses = expenses_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    top_categories = (
        expenses_qs
        .exclude(category__isnull=True)
        .values("category__name")
        .annotate(total=Sum("amount"))
        .order_by("-total")[:5]
    )

    total_topups = (
        Topup.objects.filter(date__gte=date_from, date__lte=date_to)
        .aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    )

    return render(request, "admin/dashboard.html", {
        "user_balances": user_balances,
        "total_expenses": total_expenses,
        "total_topups": total_topups,
        "top_categories": top_categories,
        "date_from": date_from,
        "date_to": date_to,
        "title": "Dashboard",
    })

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from expenses.forms import ExpenseForm
from expenses.models import Expense, ExpenseAttachment, Topup
from expenses.services.balance import get_balance
from expenses.services.expenses import (
    EditWindowExpiredError,
    NegativeBalanceError,
    create_expense,
    delete_expense,
    update_expense,
)


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


@login_required
def expense_create(request):
    form = ExpenseForm(request.POST or None, request.FILES or None)
    warning = None
    if request.method == "POST" and form.is_valid():
        try:
            expense = create_expense(
                user=request.user,
                category=form.cleaned_data["category"],
                custom_name=form.cleaned_data["custom_category_name"],
                amount=form.cleaned_data["amount"],
                expense_date=form.cleaned_data["date"],
                comment=form.cleaned_data["comment"],
                created_via="web",
                allow_negative=form.cleaned_data.get("confirm_negative", False),
            )
        except NegativeBalanceError as exc:
            warning = f"Баланс станет {exc.projected_balance} ₸. Продолжить?"
        else:
            for f in request.FILES.getlist("attachments"):
                ExpenseAttachment.objects.create(
                    expense=expense, file=f,
                    original_name=f.name, mime_type=f.content_type or "",
                    size=f.size,
                )
            messages.success(request, "Трата добавлена")
            return redirect("cabinet")
    return render(request, "expenses/expense_form.html", {"form": form, "warning": warning})


def _get_own_expense(request, pk):
    qs = Expense.objects.filter(is_deleted=False)
    if not request.user.is_admin:
        qs = qs.filter(user=request.user)
    return get_object_or_404(qs, pk=pk)


@login_required
def expense_detail(request, pk):
    expense = _get_own_expense(request, pk)
    return render(request, "expenses/expense_detail.html", {"expense": expense})


@login_required
def expense_edit(request, pk):
    expense = _get_own_expense(request, pk)
    form = ExpenseForm(request.POST or None, initial={
        "category": expense.category_id,
        "custom_category_name": expense.custom_category_name,
        "amount": expense.amount,
        "date": expense.date,
        "comment": expense.comment,
    })
    if request.method == "POST" and form.is_valid():
        try:
            update_expense(
                actor=request.user,
                expense=expense,
                category=form.cleaned_data["category"],
                custom_name=form.cleaned_data["custom_category_name"],
                amount=form.cleaned_data["amount"],
                expense_date=form.cleaned_data["date"],
                comment=form.cleaned_data["comment"],
            )
        except EditWindowExpiredError as exc:
            return HttpResponseForbidden(str(exc))
        messages.success(request, "Трата обновлена")
        return redirect("cabinet")
    return render(request, "expenses/expense_form.html", {
        "form": form, "warning": None, "edit_mode": True, "expense": expense,
    })


@login_required
def expense_delete(request, pk):
    expense = _get_own_expense(request, pk)
    if request.method == "POST":
        try:
            delete_expense(actor=request.user, expense=expense)
        except EditWindowExpiredError as exc:
            return HttpResponseForbidden(str(exc))
        messages.success(request, "Трата удалена")
        return redirect("cabinet")
    return render(request, "expenses/confirm_delete.html", {"expense": expense})

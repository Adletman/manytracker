import random
import string
from datetime import datetime, timedelta
from itertools import chain

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from expenses.forms import EmployeeTopupForm, ExpenseForm
from expenses.models import Expense, ExpenseAttachment, Topup
from expenses.services.balance import get_balance
from expenses.services.topups import create_topup
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
    expenses = list(
        Expense.objects.filter(user=request.user, is_deleted=False)
        .select_related("category")[:10]
    )
    topups = list(Topup.objects.filter(user=request.user)[:10])

    operations = sorted(
        chain(
            [{"type": "expense", "date": e.date, "label": e.category_display(),
              "amount": e.amount, "id": e.id, "created_at": e.created_at} for e in expenses],
            [{"type": "topup", "date": t.date, "label": t.comment or "Пополнение",
              "amount": t.amount, "id": t.id, "created_at": t.created_at} for t in topups],
        ),
        key=lambda x: (x["date"], x["created_at"]),
        reverse=True,
    )[:10]

    return render(request, "expenses/cabinet.html", {
        "balance": balance,
        "operations": operations,
        "active_tab": "cabinet",
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
    return render(request, "expenses/expense_form.html", {"form": form, "warning": warning, "active_tab": "cabinet"})


def _get_own_expense(request, pk):
    qs = Expense.objects.filter(is_deleted=False)
    if not request.user.is_admin:
        qs = qs.filter(user=request.user)
    return get_object_or_404(qs, pk=pk)


@login_required
def expense_detail(request, pk):
    expense = _get_own_expense(request, pk)
    return render(request, "expenses/expense_detail.html", {"expense": expense, "active_tab": "cabinet"})


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
        "form": form, "warning": None, "edit_mode": True, "expense": expense, "active_tab": "cabinet",
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
    return render(request, "expenses/confirm_delete.html", {"expense": expense, "active_tab": "cabinet"})


@login_required
def history(request):
    expenses_qs = Expense.objects.filter(user=request.user, is_deleted=False).select_related("category")
    topups_qs = Topup.objects.filter(user=request.user)
    date_from = request.GET.get("from")
    date_to = request.GET.get("to")
    if date_from:
        try:
            d = datetime.strptime(date_from, "%Y-%m-%d").date()
            expenses_qs = expenses_qs.filter(date__gte=d)
            topups_qs = topups_qs.filter(date__gte=d)
        except ValueError:
            pass
    if date_to:
        try:
            d = datetime.strptime(date_to, "%Y-%m-%d").date()
            expenses_qs = expenses_qs.filter(date__lte=d)
            topups_qs = topups_qs.filter(date__lte=d)
        except ValueError:
            pass

    operations = sorted(
        chain(
            [{"type": "expense", "date": e.date, "label": e.category_display(),
              "amount": e.amount, "id": e.id, "comment": e.comment,
              "created_at": e.created_at} for e in expenses_qs],
            [{"type": "topup", "date": t.date, "label": t.comment or "Пополнение",
              "amount": t.amount, "id": t.id, "comment": t.comment,
              "created_at": t.created_at} for t in topups_qs],
        ),
        key=lambda x: (x["date"], x["created_at"]),
        reverse=True,
    )

    return render(request, "expenses/history.html", {
        "operations": operations,
        "date_from": date_from, "date_to": date_to,
        "active_tab": "history",
    })


@login_required
def topup_create(request):
    form = EmployeeTopupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        create_topup(
            created_by=request.user,
            user=request.user,
            amount=form.cleaned_data["amount"],
            topup_date=form.cleaned_data["date"],
            comment=form.cleaned_data["comment"],
            source="employee",
        )
        messages.success(request, "Приход добавлен")
        return redirect("cabinet")
    return render(request, "expenses/topup_form.html", {"form": form, "active_tab": "cabinet"})


@login_required
def profile(request):
    link_code = None
    if request.method == "POST" and "generate_code" in request.POST:
        code = "".join(random.choices(string.digits, k=6))
        request.user.telegram_link_code = code
        request.user.telegram_link_code_expires_at = timezone.now() + timedelta(minutes=10)
        request.user.save(update_fields=["telegram_link_code", "telegram_link_code_expires_at"])
        link_code = code
    elif request.method == "POST" and "unlink_telegram" in request.POST:
        request.user.telegram_id = None
        request.user.telegram_link_code = None
        request.user.save(update_fields=["telegram_id", "telegram_link_code"])
        messages.success(request, "Telegram отвязан")
    return render(request, "expenses/profile.html", {
        "active_tab": "profile",
        "link_code": link_code,
    })


@login_required
def attachment_download(request, pk):
    qs = ExpenseAttachment.objects.select_related("expense")
    if not request.user.is_admin:
        qs = qs.filter(expense__user=request.user)
    att = get_object_or_404(qs, pk=pk)
    return FileResponse(
        att.file.open("rb"),
        as_attachment=True,
        filename=att.original_name,
        content_type=att.mime_type or "application/octet-stream",
    )

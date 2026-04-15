from datetime import date, timedelta
from decimal import Decimal
import pytest
from tests.factories import CategoryFactory
from expenses.forms import ExpenseForm


@pytest.mark.django_db
def test_expense_form_valid_with_category():
    cat = CategoryFactory()
    form = ExpenseForm(data={
        "category": cat.id, "custom_category_name": "",
        "amount": "1500.00", "date": date.today().isoformat(),
        "comment": "",
    })
    assert form.is_valid(), form.errors


@pytest.mark.django_db
def test_expense_form_valid_with_custom_name():
    form = ExpenseForm(data={
        "category": "", "custom_category_name": "Парковка",
        "amount": "500.00", "date": date.today().isoformat(),
        "comment": "",
    })
    assert form.is_valid(), form.errors


@pytest.mark.django_db
def test_expense_form_rejects_both_empty():
    form = ExpenseForm(data={
        "category": "", "custom_category_name": "",
        "amount": "500", "date": date.today().isoformat(),
    })
    assert not form.is_valid()


@pytest.mark.django_db
def test_expense_form_rejects_future_date():
    cat = CategoryFactory()
    form = ExpenseForm(data={
        "category": cat.id, "custom_category_name": "",
        "amount": "500", "date": (date.today() + timedelta(days=1)).isoformat(),
    })
    assert not form.is_valid()


@pytest.mark.django_db
def test_expense_form_rejects_very_old_date():
    cat = CategoryFactory()
    form = ExpenseForm(data={
        "category": cat.id, "custom_category_name": "",
        "amount": "500",
        "date": (date.today() - timedelta(days=365 * 3)).isoformat(),
    })
    assert not form.is_valid()

from datetime import date, timedelta
import pytest
from expenses.forms import EmployeeTopupForm


def test_topup_form_valid():
    form = EmployeeTopupForm(data={
        "amount": "10000.00",
        "date": date.today().isoformat(),
        "comment": "Получил от Серика",
    })
    assert form.is_valid(), form.errors


def test_topup_form_requires_comment():
    form = EmployeeTopupForm(data={
        "amount": "10000.00",
        "date": date.today().isoformat(),
        "comment": "",
    })
    assert not form.is_valid()
    assert "comment" in form.errors


def test_topup_form_rejects_future_date():
    form = EmployeeTopupForm(data={
        "amount": "10000.00",
        "date": (date.today() + timedelta(days=1)).isoformat(),
        "comment": "test",
    })
    assert not form.is_valid()


def test_topup_form_rejects_zero_amount():
    form = EmployeeTopupForm(data={
        "amount": "0",
        "date": date.today().isoformat(),
        "comment": "test",
    })
    assert not form.is_valid()

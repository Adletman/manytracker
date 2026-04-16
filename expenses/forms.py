from datetime import date, timedelta
from django import forms
from expenses.models import ExpenseCategory


class ExpenseForm(forms.Form):
    category = forms.ModelChoiceField(
        queryset=ExpenseCategory.objects.filter(is_active=True),
        required=False, empty_label="— выберите —", label="Категория",
    )
    custom_category_name = forms.CharField(
        max_length=64, required=False, label="Или введите своё",
    )
    amount = forms.DecimalField(
        max_digits=12, decimal_places=2, min_value=0.01, label="Сумма (₸)",
    )
    date = forms.DateField(label="Дата", widget=forms.DateInput(attrs={"type": "date"}))
    comment = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}), label="Комментарий")
    confirm_negative = forms.BooleanField(required=False, widget=forms.HiddenInput)

    def clean(self):
        cleaned = super().clean()
        cat = cleaned.get("category")
        custom = (cleaned.get("custom_category_name") or "").strip()
        if (cat is None) == (custom == ""):
            raise forms.ValidationError("Выберите категорию или введите своё название")
        cleaned["custom_category_name"] = custom
        return cleaned

    def clean_date(self):
        d = self.cleaned_data["date"]
        today = date.today()
        if d > today:
            raise forms.ValidationError("Дата не может быть в будущем")
        if d < today - timedelta(days=365 * 2):
            raise forms.ValidationError("Дата слишком старая (старше 2 лет)")
        return d


class EmployeeTopupForm(forms.Form):
    amount = forms.DecimalField(
        max_digits=12, decimal_places=2, min_value=0.01, label="Сумма (₸)",
    )
    date = forms.DateField(label="Дата", widget=forms.DateInput(attrs={"type": "date"}))
    comment = forms.CharField(
        max_length=256, label="Комментарий (от кого / за что)",
        widget=forms.Textarea(attrs={"rows": 2}),
    )

    def clean_date(self):
        d = self.cleaned_data["date"]
        today = date.today()
        if d > today:
            raise forms.ValidationError("Дата не может быть в будущем")
        if d < today - timedelta(days=365 * 2):
            raise forms.ValidationError("Дата слишком старая (старше 2 лет)")
        return d

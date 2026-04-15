from django import forms
from django.contrib.auth import authenticate


class LoginForm(forms.Form):
    username = forms.CharField(label="Логин", max_length=64)
    password = forms.CharField(label="Пароль", widget=forms.PasswordInput)

    def clean(self):
        cleaned = super().clean()
        user = authenticate(
            username=cleaned.get("username"),
            password=cleaned.get("password"),
        )
        if user is None:
            raise forms.ValidationError("Неверный логин или пароль")
        cleaned["user"] = user
        return cleaned

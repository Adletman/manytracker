from django.contrib.auth import login, logout
from django.shortcuts import redirect, render

from .forms import LoginForm


def login_view(request):
    if request.user.is_authenticated:
        return redirect("/cabinet/")
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.cleaned_data["user"])
        return redirect("/cabinet/")
    return render(request, "accounts/login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("/login/")

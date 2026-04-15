from django.urls import path
from . import views

urlpatterns = [
    path("cabinet/", views.cabinet, name="cabinet"),
    path("expenses/new/", views.cabinet, name="expense_create"),
    path("expenses/<int:pk>/", views.cabinet, name="expense_detail"),
]

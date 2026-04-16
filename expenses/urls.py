from django.urls import path
from . import views

urlpatterns = [
    path("cabinet/", views.cabinet, name="cabinet"),
    path("expenses/new/", views.expense_create, name="expense_create"),
    path("expenses/<int:pk>/", views.expense_detail, name="expense_detail"),
    path("expenses/<int:pk>/edit/", views.expense_edit, name="expense_edit"),
    path("expenses/<int:pk>/delete/", views.expense_delete, name="expense_delete"),
    path("history/", views.history, name="history"),
    path("topup/new/", views.topup_create, name="topup_create"),
    path("attachments/<int:pk>/", views.attachment_download, name="attachment_download"),
]

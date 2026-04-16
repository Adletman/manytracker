from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from expenses.admin_views import dashboard as admin_dashboard

urlpatterns = [
    path("admin/dashboard/", admin_dashboard, name="admin_dashboard"),
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("", include("expenses.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

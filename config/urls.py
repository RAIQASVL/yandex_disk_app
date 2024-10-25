from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views  # Add this line

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("src.core.urls")),
    path("", include("src.disk.urls", namespace="disk")),
]

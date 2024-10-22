from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import LogoutView
from src.core.views import SignUpView, CustomLoginView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("signup/", SignUpView.as_view(), name="signup"),
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("", include(("src.disk.urls", "disk"), namespace="disk")),
    
]

from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("login/", views.CustomLoginView.as_view(), name="login"),
    path("signup/", views.SignUpView.as_view(), name="signup"),
    path("logout/", views.CustomLogoutView.as_view(), name="logout"),
]

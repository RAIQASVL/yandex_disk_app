# src/core/views.py

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView, LogoutView
from django.views.generic import CreateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect

from src.core.forms import CustomAuthenticationForm, SignUpForm


class CustomLoginView(LoginView):
    form_class = CustomAuthenticationForm
    template_name = "registration/login.html"

    def get_success_url(self):
        return reverse_lazy("disk:file_list")

    def form_valid(self, form):
        remember_me = form.cleaned_data.get("remember_me", False)
        if not remember_me:
            self.request.session.set_expiry(0)
        return super().form_valid(form)


class SignUpView(CreateView):
    form_class = SignUpForm
    template_name = "registration/signup.html"
    success_url = reverse_lazy("disk:file_list")

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        messages.success(self.request, f"Welcome {user.username}!")
        return redirect(self.success_url)


@method_decorator(login_required, name="dispatch")
class CustomLogoutView(LogoutView):
    next_page = "core:login"

    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            username = request.user.username
            logout(request)
            messages.info(request, f"Goodbye {username}! You have been logged out.")
        return redirect(self.next_page)

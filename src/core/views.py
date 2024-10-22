from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.views.generic import CreateView
from django.urls import reverse_lazy
from .forms import SignUpForm, CustomAuthenticationForm


class SignUpView(CreateView):
    form_class = SignUpForm
    template_name = "core/signup.html"
    success_url = reverse_lazy("disk:file_list")

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return redirect(self.success_url)


class CustomLoginView(LoginView):
    form_class = CustomAuthenticationForm
    template_name = "core/login.html"

    def form_valid(self, form):
        remember_me = form.changed_data.get("remember_me")
        if not remember_me:
            # Session will be clear for closing browser
            self.request.session.set_expiry(0)
        return super().form_valid(form)

from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.urls import path, reverse_lazy

from config.ratelimit import rate_limit

from . import views

app_name = "accounts"

urlpatterns = [
    path("kayit/", views.register, name="register"),
    path(
        "giris/",
        rate_limit("login", limit=10, window_seconds=300)(
            LoginView.as_view(template_name="accounts/login.html")
        ),
        name="login",
    ),
    path("cikis/", LogoutView.as_view(next_page="polls:home"), name="logout"),
    path(
        "parola-sifirla/",
        rate_limit("password-reset", limit=5, window_seconds=600)(
            PasswordResetView.as_view(
                template_name="accounts/password_reset_form.html",
                email_template_name="accounts/password_reset_email.html",
                subject_template_name="accounts/password_reset_subject.txt",
                success_url=reverse_lazy("accounts:password_reset_done"),
            )
        ),
        name="password_reset",
    ),
    path(
        "parola-sifirla/gonderildi/",
        PasswordResetDoneView.as_view(template_name="accounts/password_reset_done.html"),
        name="password_reset_done",
    ),
    path(
        "parola-sifirla/<uidb64>/<token>/",
        PasswordResetConfirmView.as_view(
            template_name="accounts/password_reset_confirm.html",
            success_url=reverse_lazy("accounts:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "parola-sifirla/tamamlandi/",
        PasswordResetCompleteView.as_view(
            template_name="accounts/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
]

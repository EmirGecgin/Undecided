from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

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
]

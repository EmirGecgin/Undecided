from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("kayit/", views.register, name="register"),
    path("giris/", LoginView.as_view(template_name="accounts/login.html"), name="login"),
    path("cikis/", LogoutView.as_view(next_page="polls:home"), name="logout"),
]

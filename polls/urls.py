from django.urls import path

from . import views

app_name = "polls"

urlpatterns = [
    path("", views.home, name="home"),
    path("anket/olustur/", views.create, name="create"),
    path("anket/<int:pk>/", views.detail, name="detail"),
    path("anket/<int:pk>/oy/", views.vote, name="vote"),
    path("anket/<int:pk>/sil/", views.delete, name="delete"),
    path("u/<str:username>/", views.profile, name="profile"),
]

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .forms import UserAdminChangeForm, UserAdminCreationForm
from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    model = User
    add_form = UserAdminCreationForm
    form = UserAdminChangeForm

    fieldsets = (
        (None, {"fields": ("username", "email", "password")}),
        ("İzinler", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Önemli tarihler", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"fields": ("username", "email", "password1", "password2")}),
    )
    list_display = ("username", "email", "is_staff", "is_active", "date_joined")
    search_fields = ("username", "email")
    ordering = ("-date_joined",)

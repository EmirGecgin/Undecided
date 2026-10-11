from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models

username_validator = RegexValidator(
    regex=r"^[a-z0-9_]{3,20}$",
    message="Kullanıcı adı 3-20 karakter olmalı ve yalnızca küçük harf, rakam, alt çizgi (_) içermelidir.",
)


class User(AbstractUser):
    email = models.EmailField("e-posta", unique=True)
    username = models.CharField(
        "kullanıcı adı",
        max_length=20,
        unique=True,
        validators=[username_validator],
        help_text="3-20 karakter, yalnızca küçük harf, rakam ve alt çizgi (_).",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def save(self, *args, **kwargs):
        self.email = self.email.lower()
        self.username = self.username.lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username

from django.conf import settings
from django.core.validators import MaxValueValidator, MinLengthValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Poll(models.Model):
    CATEGORY_GENEL = "genel"
    CATEGORY_YEMEK = "yemek"
    CATEGORY_EGLENCE = "eglence"
    CATEGORY_ALISVERIS = "alisveris"
    CATEGORY_TEKNOLOJI = "teknoloji"
    CATEGORY_SPOR = "spor"
    CATEGORY_CHOICES = [
        (CATEGORY_GENEL, "Genel"),
        (CATEGORY_YEMEK, "Yemek"),
        (CATEGORY_EGLENCE, "Eğlence"),
        (CATEGORY_ALISVERIS, "Alışveriş"),
        (CATEGORY_TEKNOLOJI, "Teknoloji"),
        (CATEGORY_SPOR, "Spor"),
    ]

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="polls"
    )
    question = models.CharField(
        "soru",
        max_length=200,
        validators=[MinLengthValidator(5, message="Soru en az 5 karakter olmalı.")],
    )
    description = models.TextField("açıklama", max_length=500, blank=True)
    category = models.CharField(
        "kategori", max_length=20, choices=CATEGORY_CHOICES, default=CATEGORY_GENEL
    )
    expires_at = models.DateTimeField("bitiş zamanı", null=True, blank=True)
    created_at = models.DateTimeField("oluşturulma zamanı", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.question

    @property
    def is_closed(self):
        return self.expires_at is not None and self.expires_at <= timezone.now()


class Option(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name="options")
    text = models.CharField("metin", max_length=80)
    order = models.PositiveSmallIntegerField("sıra", validators=[MaxValueValidator(4)])

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.text


class Vote(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name="votes")
    option = models.ForeignKey(Option, on_delete=models.CASCADE, related_name="votes")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True
    )
    voter_token = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["poll", "user"],
                condition=Q(user__isnull=False),
                name="unique_vote_per_user",
            ),
            models.UniqueConstraint(
                fields=["poll", "voter_token"],
                condition=Q(voter_token__isnull=False),
                name="unique_vote_per_voter_token",
            ),
            models.CheckConstraint(
                check=Q(user__isnull=False) | Q(voter_token__isnull=False),
                name="vote_has_user_or_voter_token",
            ),
        ]

    def __str__(self):
        return f"{self.poll_id} -> {self.option_id}"

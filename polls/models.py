from django.conf import settings
from django.core.validators import MaxValueValidator, MinLengthValidator
from django.db import models
from django.db.models import Q


class Poll(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="polls"
    )
    question = models.CharField(
        "soru",
        max_length=200,
        validators=[MinLengthValidator(5, message="Soru en az 5 karakter olmalı.")],
    )
    description = models.TextField("açıklama", max_length=500, blank=True)
    created_at = models.DateTimeField("oluşturulma zamanı", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.question


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

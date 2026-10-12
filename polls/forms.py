from django import forms
from django.core.validators import MinLengthValidator

from .models import Poll

MIN_OPTIONS = 2
MAX_OPTIONS = 5

DURATION_CHOICES = [
    ("", "Süresiz"),
    ("1", "1 saat"),
    ("6", "6 saat"),
    ("24", "24 saat"),
    ("72", "3 gün"),
    ("168", "7 gün"),
]


class PollCreateForm(forms.Form):
    question = forms.CharField(
        label="Soru",
        max_length=200,
        validators=[MinLengthValidator(5, message="Soru en az 5 karakter olmalı.")],
    )
    description = forms.CharField(
        label="Açıklama",
        max_length=500,
        required=False,
        widget=forms.Textarea,
    )
    category = forms.ChoiceField(
        label="Kategori", choices=Poll.CATEGORY_CHOICES, initial=Poll.CATEGORY_GENEL
    )
    duration_hours = forms.ChoiceField(
        label="Süre", choices=DURATION_CHOICES, required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for i in range(1, MAX_OPTIONS + 1):
            self.fields[f"option_{i}"] = forms.CharField(
                label=f"Seçenek {i}", max_length=80, required=False
            )

    def clean(self):
        cleaned_data = super().clean()
        options = []
        seen = set()
        for i in range(1, MAX_OPTIONS + 1):
            value = (cleaned_data.get(f"option_{i}") or "").strip()
            if not value:
                continue
            key = value.lower()
            if key in seen:
                self.add_error(f"option_{i}", "Bu seçenek zaten eklendi.")
                continue
            seen.add(key)
            options.append(value)

        if len(options) < MIN_OPTIONS:
            raise forms.ValidationError(f"En az {MIN_OPTIONS} seçenek girmelisin.")
        if len(options) > MAX_OPTIONS:
            raise forms.ValidationError(f"En fazla {MAX_OPTIONS} seçenek girebilirsin.")

        cleaned_data["options"] = options
        return cleaned_data

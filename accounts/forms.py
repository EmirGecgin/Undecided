from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.contrib.auth.password_validation import validate_password

from .models import User, username_validator


class UserAdminCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("username", "email")


class UserAdminChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = "__all__"


class RegistrationForm(forms.ModelForm):
    password1 = forms.CharField(label="Parola", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Parola (tekrar)", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ("username", "email")

    def clean_username(self):
        username = self.cleaned_data["username"].strip().lower()
        username_validator(username)
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Bu kullanıcı adı zaten alınmış.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Bu e-posta adresi zaten kayıtlı.")
        return email

    def clean_password1(self):
        password1 = self.cleaned_data.get("password1")
        if password1:
            validate_password(password1)
        return password1

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "Parolalar birbiriyle eşleşmiyor.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user

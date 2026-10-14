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
        # Python'un locale-bağımsız .lower()'ı Türkçe büyük 'İ' harfini tek bir ASCII
        # 'i' değil, iki karakterlik "i" + birleşik nokta işaretine çeviriyor (örn.
        # "İREM" -> "i̇rem"), bu da aşağıdaki a-z regex'ini her zaman başarısız kılıyordu.
        # Önce 'İ'yi düz ASCII 'i'ye indirip öyle küçültüyoruz.
        username = self.cleaned_data["username"].strip().replace("İ", "i").lower()
        username_validator(username)
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Bu kullanıcı adı zaten alınmış.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Bu e-posta adresi zaten kayıtlı.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "Parolalar birbiriyle eşleşmiyor.")
        return cleaned_data

    def _post_clean(self):
        # self.instance henüz username/email ile bu adımda doldurulur (construct_instance
        # super()._post_clean() içinde çalışır), bu yüzden UserAttributeSimilarityValidator
        # (parola kullanıcı adı/e-posta ile aynı olamaz) ancak burada doğru çalışabilir —
        # clean_password1'de self.instance boş olduğu için bu kontrol sessizce atlanıyordu.
        super()._post_clean()
        password1 = self.cleaned_data.get("password1")
        if password1:
            try:
                validate_password(password1, self.instance)
            except forms.ValidationError as error:
                self.add_error("password1", error)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user

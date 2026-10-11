from django.test import TestCase
from django.urls import reverse

from .models import User

VALID_PASSWORD = "guclu-parola-123"


class UserModelTests(TestCase):
    def test_username_and_email_stored_lowercase(self):
        user = User.objects.create_user(
            username="AliVeli", email="Ali@Example.com", password=VALID_PASSWORD
        )
        self.assertEqual(user.username, "aliveli")
        self.assertEqual(user.email, "ali@example.com")


class RegistrationViewTests(TestCase):
    def _post_register(self, **overrides):
        data = {
            "username": "merhaba",
            "email": "merhaba@example.com",
            "password1": VALID_PASSWORD,
            "password2": VALID_PASSWORD,
        }
        data.update(overrides)
        return self.client.post(reverse("accounts:register"), data)

    def test_register_logs_in_and_redirects_home(self):
        response = self._post_register()
        self.assertRedirects(response, reverse("polls:home"))
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_duplicate_username_case_insensitive_rejected(self):
        User.objects.create_user(
            username="merhaba", email="once@example.com", password=VALID_PASSWORD
        )
        response = self._post_register(username="MERHABA", email="farkli@example.com")
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"], "username", "Bu kullanıcı adı zaten alınmış."
        )

    def test_duplicate_email_case_insensitive_rejected(self):
        User.objects.create_user(
            username="ilkkullanici", email="ayni@example.com", password=VALID_PASSWORD
        )
        response = self._post_register(username="farklikullanici", email="AYNI@EXAMPLE.COM")
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"], "email", "Bu e-posta adresi zaten kayıtlı."
        )

    def test_invalid_username_rejected(self):
        response = self._post_register(username="ab", email="kisa@example.com")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["form"].is_valid())

    def test_password_mismatch_rejected(self):
        response = self._post_register(password2="farkli-parola-456")
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"], "password2", "Parolalar birbiriyle eşleşmiyor."
        )


class LoginLogoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="girisyapan", email="giris@example.com", password=VALID_PASSWORD
        )

    def test_login_with_email(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "giris@example.com", "password": VALID_PASSWORD},
        )
        self.assertRedirects(response, reverse("polls:home"))

    def test_logout_requires_post(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("accounts:logout"))
        self.assertEqual(response.status_code, 405)

    def test_email_not_in_home_page(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("polls:home"))
        self.assertNotContains(response, "giris@example.com")

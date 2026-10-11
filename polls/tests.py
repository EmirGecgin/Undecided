import uuid

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from accounts.models import User

from .models import Option, Poll, Vote

VALID_PASSWORD = "guclu-parola-123"
VALID_QUESTION = "Yeterince uzun bir soru mu?"


class PollCreateViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="sahipkullanici", email="sahip@example.com", password=VALID_PASSWORD
        )

    def _post_create(self, **overrides):
        data = {
            "question": VALID_QUESTION,
            "description": "",
            "option_1": "Sinema",
            "option_2": "Restoran",
            "option_3": "",
            "option_4": "",
            "option_5": "",
        }
        data.update(overrides)
        return self.client.post(reverse("polls:create"), data)

    def test_create_requires_login_redirects_with_next(self):
        response = self.client.get(reverse("polls:create"))
        expected = f"{reverse('accounts:login')}?next={reverse('polls:create')}"
        self.assertRedirects(response, expected, fetch_redirect_response=False)

    def test_valid_poll_is_created_with_options(self):
        self.client.force_login(self.user)
        response = self._post_create()
        poll = Poll.objects.get(question=VALID_QUESTION)
        self.assertRedirects(response, reverse("polls:detail", args=[poll.pk]))
        self.assertEqual(poll.author, self.user)
        self.assertEqual(list(poll.options.values_list("text", flat=True)), ["Sinema", "Restoran"])

    def test_single_option_rejected(self):
        self.client.force_login(self.user)
        response = self._post_create(option_2="")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Poll.objects.count(), 0)

    def test_six_options_are_capped_at_five(self):
        self.client.force_login(self.user)
        data = {
            "question": VALID_QUESTION,
            "description": "",
            "option_1": "A",
            "option_2": "B",
            "option_3": "C",
            "option_4": "D",
            "option_5": "E",
            "option_6": "F",
        }
        self.client.post(reverse("polls:create"), data)
        poll = Poll.objects.get(question=VALID_QUESTION)
        self.assertEqual(poll.options.count(), 5)
        self.assertFalse(poll.options.filter(text="F").exists())

    def test_duplicate_option_text_case_insensitive_rejected(self):
        self.client.force_login(self.user)
        response = self._post_create(option_1="Sinema", option_2="SINEMA")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Poll.objects.count(), 0)

    def test_short_question_rejected(self):
        self.client.force_login(self.user)
        response = self._post_create(question="Kısa")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Poll.objects.count(), 0)


class PollDeleteViewTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="sahipkullanici", email="sahip@example.com", password=VALID_PASSWORD
        )
        self.other = User.objects.create_user(
            username="digerkullanici", email="diger@example.com", password=VALID_PASSWORD
        )
        self.poll = Poll.objects.create(author=self.owner, question=VALID_QUESTION)
        Option.objects.create(poll=self.poll, text="A", order=0)
        Option.objects.create(poll=self.poll, text="B", order=1)

    def test_owner_can_delete(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse("polls:delete", args=[self.poll.pk]))
        self.assertRedirects(response, reverse("polls:home"))
        self.assertFalse(Poll.objects.filter(pk=self.poll.pk).exists())

    def test_non_owner_gets_403(self):
        self.client.force_login(self.other)
        response = self.client.post(reverse("polls:delete", args=[self.poll.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Poll.objects.filter(pk=self.poll.pk).exists())

    def test_delete_requires_post(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("polls:delete", args=[self.poll.pk]))
        self.assertEqual(response.status_code, 405)


class HomeAndProfileViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="sahipkullanici", email="sahip@example.com", password=VALID_PASSWORD
        )

    def test_home_lists_poll_with_username_and_shows_no_email(self):
        poll = Poll.objects.create(author=self.user, question=VALID_QUESTION)
        Option.objects.create(poll=poll, text="A", order=0)
        Option.objects.create(poll=poll, text="B", order=1)

        response = self.client.get(reverse("polls:home"))
        self.assertContains(response, "@" + self.user.username)
        self.assertContains(response, poll.question)
        self.assertNotContains(response, self.user.email)

    def test_populer_tab_orders_by_vote_count(self):
        poll_low = Poll.objects.create(author=self.user, question="Az oylu bir soru mu?")
        Option.objects.create(poll=poll_low, text="A", order=0)
        Option.objects.create(poll=poll_low, text="B", order=1)

        poll_high = Poll.objects.create(author=self.user, question="Çok oylu bir soru mu?")
        opt = Option.objects.create(poll=poll_high, text="A", order=0)
        Option.objects.create(poll=poll_high, text="B", order=1)
        Vote.objects.create(poll=poll_high, option=opt, voter_token=uuid.uuid4())

        response = self.client.get(reverse("polls:home"), {"sekme": "populer"})
        polls = list(response.context["page_obj"])
        self.assertEqual(polls[0].pk, poll_high.pk)

    def test_profile_page_lists_only_that_users_polls(self):
        other = User.objects.create_user(
            username="digerkullanici", email="diger@example.com", password=VALID_PASSWORD
        )
        mine = Poll.objects.create(author=self.user, question=VALID_QUESTION)
        Option.objects.create(poll=mine, text="A", order=0)
        Option.objects.create(poll=mine, text="B", order=1)
        others = Poll.objects.create(author=other, question="Diğer kullanıcının sorusu mu?")
        Option.objects.create(poll=others, text="A", order=0)
        Option.objects.create(poll=others, text="B", order=1)

        response = self.client.get(reverse("polls:profile", args=[self.user.username]))
        self.assertContains(response, mine.question)
        self.assertNotContains(response, others.question)


class VoteModelConstraintTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="oycu", email="oycu@example.com", password=VALID_PASSWORD
        )
        self.poll = Poll.objects.create(author=self.user, question=VALID_QUESTION)
        self.option_a = Option.objects.create(poll=self.poll, text="A", order=0)
        self.option_b = Option.objects.create(poll=self.poll, text="B", order=1)

    def test_vote_requires_user_or_voter_token(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Vote.objects.create(poll=self.poll, option=self.option_a)

    def test_duplicate_vote_for_same_user_rejected(self):
        Vote.objects.create(poll=self.poll, option=self.option_a, user=self.user)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Vote.objects.create(poll=self.poll, option=self.option_b, user=self.user)

    def test_duplicate_vote_for_same_voter_token_rejected(self):
        token = uuid.uuid4()
        Vote.objects.create(poll=self.poll, option=self.option_a, voter_token=token)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Vote.objects.create(poll=self.poll, option=self.option_b, voter_token=token)

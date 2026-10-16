import uuid
from datetime import timedelta

from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from config.ratelimit import rate_limit

from .models import Option, Poll, Vote

VALID_PASSWORD = "guclu-parola-123"
VALID_QUESTION = "Yeterince uzun bir soru mu?"


class PollCreateViewTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username="sahipkullanici", email="sahip@example.com", password=VALID_PASSWORD
        )

    def _post_create(self, **overrides):
        data = {
            "question": VALID_QUESTION,
            "description": "",
            "category": Poll.CATEGORY_GENEL,
            "duration_hours": "",
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
            "category": Poll.CATEGORY_GENEL,
            "duration_hours": "",
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
        cache.clear()
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
        cache.clear()
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

    def test_home_shows_passive_preview_before_voting(self):
        poll = Poll.objects.create(author=self.user, question=VALID_QUESTION)
        Option.objects.create(poll=poll, text="A", order=0)
        Option.objects.create(poll=poll, text="B", order=1)

        response = self.client.get(reverse("polls:home"))
        self.assertNotContains(response, "vote-form")
        self.assertContains(response, "poll-results-preview")
        self.assertNotContains(response, "— %")

    def test_home_shows_real_results_after_voting(self):
        poll = Poll.objects.create(author=self.user, question=VALID_QUESTION)
        option_a = Option.objects.create(poll=poll, text="A", order=0)
        Option.objects.create(poll=poll, text="B", order=1)
        self.client.post(
            reverse("polls:vote", args=[poll.pk]),
            {"option_id": option_a.pk},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        response = self.client.get(reverse("polls:home"))
        self.assertNotContains(response, "vote-form")
        self.assertContains(response, "%100")

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
        cache.clear()
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


class VoteViewTests(TestCase):
    def setUp(self):
        cache.clear()
        self.owner = User.objects.create_user(
            username="sahipkullanici", email="sahip@example.com", password=VALID_PASSWORD
        )
        self.member = User.objects.create_user(
            username="uyekullanici", email="uye@example.com", password=VALID_PASSWORD
        )
        self.poll = Poll.objects.create(author=self.owner, question=VALID_QUESTION)
        self.option_a = Option.objects.create(poll=self.poll, text="Sinema", order=0)
        self.option_b = Option.objects.create(poll=self.poll, text="Restoran", order=1)

    def _vote(self, option, ajax=True, **extra):
        kwargs = {}
        if ajax:
            kwargs["HTTP_X_REQUESTED_WITH"] = "XMLHttpRequest"
        kwargs.update(extra)
        return self.client.post(
            reverse("polls:vote", args=[self.poll.pk]),
            {"option_id": option.pk},
            **kwargs,
        )

    def test_guest_can_vote_once_then_blocked(self):
        response = self._vote(self.option_a)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["total_votes"], 1)
        self.assertEqual(data["voted_option_id"], self.option_a.pk)

        response2 = self._vote(self.option_b)
        self.assertEqual(response2.status_code, 409)
        data2 = response2.json()
        self.assertFalse(data2["ok"])
        self.assertEqual(data2["voted_option_id"], self.option_a.pk)
        self.assertEqual(Vote.objects.filter(poll=self.poll).count(), 1)

    def test_member_can_vote_once_then_blocked(self):
        self.client.force_login(self.member)
        response = self._vote(self.option_a)
        self.assertTrue(response.json()["ok"])

        response2 = self._vote(self.option_b)
        self.assertEqual(response2.status_code, 409)
        self.assertEqual(Vote.objects.filter(poll=self.poll, user=self.member).count(), 1)

    def test_percentages_and_counts_are_correct(self):
        self.client.force_login(self.member)
        self._vote(self.option_a)

        other = User.objects.create_user(
            username="ucuncukullanici", email="ucuncu@example.com", password=VALID_PASSWORD
        )
        self.client.force_login(other)
        response = self._vote(self.option_a)
        data = response.json()

        self.assertEqual(data["total_votes"], 2)
        by_id = {r["option_id"]: r for r in data["results"]}
        self.assertEqual(by_id[self.option_a.pk]["votes"], 2)
        self.assertEqual(by_id[self.option_a.pk]["percent"], 100)
        self.assertEqual(by_id[self.option_b.pk]["votes"], 0)
        total_percent = sum(r["percent"] for r in data["results"])
        self.assertEqual(total_percent, 100)

    def test_option_from_another_poll_returns_400(self):
        other_poll = Poll.objects.create(author=self.owner, question="Başka bir soru mu?")
        other_option = Option.objects.create(poll=other_poll, text="X", order=0)

        response = self._vote(other_option)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Vote.objects.count(), 0)

    def test_non_ajax_vote_redirects_to_detail(self):
        response = self._vote(self.option_a, ajax=False)
        self.assertRedirects(response, reverse("polls:detail", args=[self.poll.pk]))
        self.assertEqual(Vote.objects.filter(poll=self.poll).count(), 1)

    def test_detail_shows_results_after_voting(self):
        self._vote(self.option_a)
        response = self.client.get(reverse("polls:detail", args=[self.poll.pk]))
        self.assertTrue(response.context["poll"].show_results)
        self.assertContains(response, "poll-results")

    def test_detail_shows_results_to_owner_without_voting(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("polls:detail", args=[self.poll.pk]))
        self.assertTrue(response.context["poll"].show_results)
        self.assertContains(response, "vote-form")

    def test_owner_can_vote_on_own_poll(self):
        self.client.force_login(self.owner)
        response = self._vote(self.option_a)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertEqual(
            Vote.objects.filter(poll=self.poll, user=self.owner, option=self.option_a).count(), 1
        )

    def test_detail_hides_vote_form_from_owner_after_voting(self):
        self.client.force_login(self.owner)
        self._vote(self.option_a)
        response = self.client.get(reverse("polls:detail", args=[self.poll.pk]))
        self.assertNotContains(response, "vote-form")

    def test_detail_hides_results_before_voting_for_others(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse("polls:detail", args=[self.poll.pk]))
        self.assertFalse(response.context["poll"].show_results)
        self.assertContains(response, "vote-form")

    def test_populer_tab_orders_by_real_votes(self):
        quiet_poll = Poll.objects.create(author=self.owner, question="Sessiz bir soru mu?")
        Option.objects.create(poll=quiet_poll, text="A", order=0)
        Option.objects.create(poll=quiet_poll, text="B", order=1)

        self._vote(self.option_a)

        response = self.client.get(reverse("polls:home"), {"sekme": "populer"})
        polls = list(response.context["page_obj"])
        self.assertEqual(polls[0].pk, self.poll.pk)


class PollExpiryTests(TestCase):
    def setUp(self):
        cache.clear()
        self.owner = User.objects.create_user(
            username="sahipkullanici", email="sahip@example.com", password=VALID_PASSWORD
        )
        self.other = User.objects.create_user(
            username="digerkullanici", email="diger@example.com", password=VALID_PASSWORD
        )
        self.poll = Poll.objects.create(
            author=self.owner,
            question=VALID_QUESTION,
            expires_at=timezone.now() - timedelta(hours=1),
        )
        self.option_a = Option.objects.create(poll=self.poll, text="A", order=0)
        self.option_b = Option.objects.create(poll=self.poll, text="B", order=1)

    def test_is_closed_true_when_expired(self):
        self.assertTrue(self.poll.is_closed)

    def test_vote_on_closed_poll_rejected(self):
        response = self.client.post(
            reverse("polls:vote", args=[self.poll.pk]),
            {"option_id": self.option_a.pk},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(Vote.objects.count(), 0)

    def test_closed_poll_shows_results_to_everyone(self):
        self.client.force_login(self.other)
        response = self.client.get(reverse("polls:detail", args=[self.poll.pk]))
        self.assertTrue(response.context["poll"].show_results)
        self.assertContains(response, "Kapandı")

    def test_poll_with_future_expiry_is_not_closed(self):
        poll = Poll.objects.create(
            author=self.owner,
            question="Henüz acik bir soru mu?",
            expires_at=timezone.now() + timedelta(hours=1),
        )
        self.assertFalse(poll.is_closed)


class SearchAndCategoryTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username="sahipkullanici", email="sahip@example.com", password=VALID_PASSWORD
        )

    def _create_poll(self, question, category):
        poll = Poll.objects.create(author=self.user, question=question, category=category)
        Option.objects.create(poll=poll, text="A", order=0)
        Option.objects.create(poll=poll, text="B", order=1)
        return poll

    def test_search_filters_by_question(self):
        self._create_poll("Pizza mi yesem?", Poll.CATEGORY_YEMEK)
        self._create_poll("Film mi izlesem?", Poll.CATEGORY_EGLENCE)

        response = self.client.get(reverse("polls:home"), {"q": "pizza"})
        self.assertContains(response, "Pizza mi yesem?")
        self.assertNotContains(response, "Film mi izlesem?")

    def test_category_filter(self):
        self._create_poll("Pizza mi yesem?", Poll.CATEGORY_YEMEK)
        self._create_poll("Film mi izlesem?", Poll.CATEGORY_EGLENCE)

        response = self.client.get(reverse("polls:home"), {"kategori": Poll.CATEGORY_YEMEK})
        self.assertContains(response, "Pizza mi yesem?")
        self.assertNotContains(response, "Film mi izlesem?")

    def test_invalid_category_is_ignored(self):
        self._create_poll("Pizza mi yesem?", Poll.CATEGORY_YEMEK)

        response = self.client.get(reverse("polls:home"), {"kategori": "uydurma"})
        self.assertContains(response, "Pizza mi yesem?")


class VoterIDMiddlewareTests(TestCase):
    def test_malformed_voter_id_cookie_is_replaced_not_fatal(self):
        self.client.cookies["voter_id"] = "not-a-valid-uuid"
        response = self.client.get(reverse("polls:home"))
        self.assertEqual(response.status_code, 200)
        new_cookie = response.cookies.get("voter_id")
        self.assertIsNotNone(new_cookie)
        uuid.UUID(new_cookie.value)

    def test_valid_voter_id_cookie_is_kept_unchanged(self):
        token = str(uuid.uuid4())
        self.client.cookies["voter_id"] = token
        response = self.client.get(reverse("polls:home"))
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.cookies.get("voter_id"))
        self.assertEqual(self.client.cookies["voter_id"].value, token)


class RateLimitTests(TestCase):
    def setUp(self):
        cache.clear()

    def _request(self, remote_addr="1.2.3.4"):
        factory = RequestFactory()
        request = factory.post(
            "/dummy/", HTTP_X_REQUESTED_WITH="XMLHttpRequest", REMOTE_ADDR=remote_addr
        )
        request.user = AnonymousUser()
        return request

    def test_blocks_after_limit_then_recovers_after_window(self):
        calls = []

        @rate_limit("test-endpoint", limit=2, window_seconds=60)
        def dummy_view(request):
            calls.append(1)
            return JsonResponse({"ok": True})

        self.assertEqual(dummy_view(self._request()).status_code, 200)
        self.assertEqual(dummy_view(self._request()).status_code, 200)
        blocked = dummy_view(self._request())
        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(len(calls), 2)

    def test_limit_is_tracked_per_client(self):
        @rate_limit("test-endpoint-2", limit=1, window_seconds=60)
        def dummy_view(request):
            return JsonResponse({"ok": True})

        self.assertEqual(dummy_view(self._request("1.1.1.1")).status_code, 200)
        self.assertEqual(dummy_view(self._request("2.2.2.2")).status_code, 200)
        self.assertEqual(dummy_view(self._request("1.1.1.1")).status_code, 429)

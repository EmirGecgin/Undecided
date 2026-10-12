import uuid
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Count, Prefetch, Q
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import PollCreateForm
from .models import Option, Poll, Vote

User = get_user_model()

PAGE_SIZE = 20


def _is_ajax(request):
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def _voter_token(request):
    return uuid.UUID(request.voter_id)


def _viewer_vote_filter(request):
    if request.user.is_authenticated:
        return Q(user=request.user)
    return Q(voter_token=_voter_token(request))


def _existing_vote(poll, request):
    if request.user.is_authenticated:
        return Vote.objects.filter(poll=poll, user=request.user).first()
    return Vote.objects.filter(poll=poll, voter_token=_voter_token(request)).first()


def _polls_queryset(request):
    options_qs = Option.objects.annotate(vote_count=Count("votes")).order_by("order")
    viewer_votes_qs = Vote.objects.filter(_viewer_vote_filter(request))
    return (
        Poll.objects.select_related("author")
        .prefetch_related(Prefetch("options", queryset=options_qs))
        .prefetch_related(Prefetch("votes", queryset=viewer_votes_qs, to_attr="viewer_votes"))
        .annotate(vote_count=Count("votes"))
    )


def _attach_viewer_state(poll, request):
    viewer_vote = poll.viewer_votes[0] if poll.viewer_votes else None
    is_owner = request.user.is_authenticated and poll.author_id == request.user.id

    poll.voted_option_id = viewer_vote.option_id if viewer_vote else None
    poll.show_results = bool(viewer_vote) or is_owner or poll.is_closed

    total = poll.vote_count
    for option in poll.options.all():
        option.percent = round(option.vote_count * 100 / total) if total else 0
    return poll


def _build_vote_payload(poll, voted_option_id, ok=True, error=None):
    options = list(poll.options.annotate(vote_count=Count("votes")).order_by("order"))
    total_votes = sum(option.vote_count for option in options)
    results = [
        {
            "option_id": option.id,
            "text": option.text,
            "votes": option.vote_count,
            "percent": round(option.vote_count * 100 / total_votes) if total_votes else 0,
        }
        for option in options
    ]
    payload = {
        "ok": ok,
        "total_votes": total_votes,
        "results": results,
        "voted_option_id": voted_option_id,
    }
    if error:
        payload["error"] = error
    return payload


def home(request):
    tab = request.GET.get("sekme")
    query = request.GET.get("q", "").strip()
    category = request.GET.get("kategori", "")

    polls = _polls_queryset(request)
    if query:
        polls = polls.filter(question__icontains=query)
    if category in dict(Poll.CATEGORY_CHOICES):
        polls = polls.filter(category=category)
    else:
        category = ""

    if tab == "populer":
        polls = polls.order_by("-vote_count", "-created_at")
    else:
        tab = "en-yeni"
        polls = polls.order_by("-created_at")

    page_obj = Paginator(polls, PAGE_SIZE).get_page(request.GET.get("sayfa"))
    for poll in page_obj:
        _attach_viewer_state(poll, request)

    return render(
        request,
        "polls/home.html",
        {
            "page_obj": page_obj,
            "tab": tab,
            "query": query,
            "category": category,
            "categories": Poll.CATEGORY_CHOICES,
        },
    )


def detail(request, pk):
    poll = get_object_or_404(_polls_queryset(request), pk=pk)
    _attach_viewer_state(poll, request)
    return render(request, "polls/detail.html", {"poll": poll})


@login_required
def create(request):
    if request.method == "POST":
        form = PollCreateForm(request.POST)
        if form.is_valid():
            duration = form.cleaned_data.get("duration_hours")
            expires_at = (
                timezone.now() + timedelta(hours=int(duration)) if duration else None
            )
            poll = Poll.objects.create(
                author=request.user,
                question=form.cleaned_data["question"],
                description=form.cleaned_data["description"],
                category=form.cleaned_data["category"],
                expires_at=expires_at,
            )
            Option.objects.bulk_create(
                Option(poll=poll, text=text, order=index)
                for index, text in enumerate(form.cleaned_data["options"])
            )
            return redirect("polls:detail", pk=poll.pk)
    else:
        form = PollCreateForm()
    return render(request, "polls/poll_form.html", {"form": form})


@require_POST
@login_required
def delete(request, pk):
    poll = get_object_or_404(Poll, pk=pk)
    if poll.author_id != request.user.id:
        return HttpResponseForbidden("Bu anketi silme yetkin yok.")
    poll.delete()
    return redirect("polls:home")


@require_POST
def vote(request, pk):
    poll = get_object_or_404(Poll, pk=pk)

    if poll.is_closed:
        existing = _existing_vote(poll, request)
        payload = _build_vote_payload(
            poll,
            existing.option_id if existing else None,
            ok=False,
            error="Bu anketin süresi doldu.",
        )
        if _is_ajax(request):
            return JsonResponse(payload, status=409)
        messages.error(request, payload["error"])
        return redirect("polls:detail", pk=poll.pk)

    option_id = request.POST.get("option_id")

    option = Option.objects.filter(pk=option_id, poll=poll).first()
    if option is None:
        payload = {"ok": False, "error": "Geçersiz seçenek."}
        if _is_ajax(request):
            return JsonResponse(payload, status=400)
        messages.error(request, payload["error"])
        return redirect("polls:detail", pk=poll.pk)

    vote_kwargs = {"poll": poll, "option": option}
    if request.user.is_authenticated:
        vote_kwargs["user"] = request.user
    else:
        vote_kwargs["voter_token"] = _voter_token(request)

    try:
        with transaction.atomic():
            Vote.objects.create(**vote_kwargs)
    except IntegrityError:
        existing = _existing_vote(poll, request)
        voted_option_id = existing.option_id if existing else None
        payload = _build_vote_payload(
            poll, voted_option_id, ok=False, error="Bu ankete zaten oy verdin."
        )
        if _is_ajax(request):
            return JsonResponse(payload, status=409)
        messages.error(request, payload["error"])
        return redirect("polls:detail", pk=poll.pk)

    payload = _build_vote_payload(poll, option.id, ok=True)
    if _is_ajax(request):
        return JsonResponse(payload)
    return redirect("polls:detail", pk=poll.pk)


def profile(request, username):
    profile_user = get_object_or_404(User, username=username.lower())
    polls = _polls_queryset(request).filter(author=profile_user).order_by("-created_at")
    page_obj = Paginator(polls, PAGE_SIZE).get_page(request.GET.get("sayfa"))
    for poll in page_obj:
        _attach_viewer_state(poll, request)
    return render(
        request, "polls/profile.html", {"profile_user": profile_user, "page_obj": page_obj}
    )

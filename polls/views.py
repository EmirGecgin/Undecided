from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import PollCreateForm
from .models import Option, Poll

User = get_user_model()

PAGE_SIZE = 20


def _polls_queryset():
    return (
        Poll.objects.select_related("author")
        .prefetch_related("options")
        .annotate(vote_count=Count("votes"))
    )


def home(request):
    tab = request.GET.get("sekme")
    polls = _polls_queryset()
    if tab == "populer":
        polls = polls.order_by("-vote_count", "-created_at")
    else:
        tab = "en-yeni"
        polls = polls.order_by("-created_at")

    page_obj = Paginator(polls, PAGE_SIZE).get_page(request.GET.get("sayfa"))

    return render(request, "polls/home.html", {"page_obj": page_obj, "tab": tab})


def detail(request, pk):
    poll = get_object_or_404(_polls_queryset(), pk=pk)
    return render(request, "polls/detail.html", {"poll": poll})


@login_required
def create(request):
    if request.method == "POST":
        form = PollCreateForm(request.POST)
        if form.is_valid():
            poll = Poll.objects.create(
                author=request.user,
                question=form.cleaned_data["question"],
                description=form.cleaned_data["description"],
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


def profile(request, username):
    profile_user = get_object_or_404(User, username=username.lower())
    polls = _polls_queryset().filter(author=profile_user).order_by("-created_at")
    page_obj = Paginator(polls, PAGE_SIZE).get_page(request.GET.get("sayfa"))
    return render(
        request, "polls/profile.html", {"profile_user": profile_user, "page_obj": page_obj}
    )

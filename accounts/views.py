from django.contrib.auth import login
from django.db import IntegrityError
from django.shortcuts import redirect, render

from .forms import RegistrationForm


def register(request):
    if request.user.is_authenticated:
        return redirect("polls:home")

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
            except IntegrityError:
                # form.is_valid() burada benzersizliği kontrol etmişti, ama aynı
                # kullanıcı adı/e-posta ile eşzamanlı bir kayıt araya girip onu
                # geçersiz kılmış olabilir (check-then-act yarışı).
                form.add_error(
                    None,
                    "Bu kullanıcı adı veya e-posta az önce alındı. Lütfen tekrar dene.",
                )
            else:
                login(request, user)
                return redirect("polls:home")
    else:
        form = RegistrationForm()

    return render(request, "accounts/register.html", {"form": form})

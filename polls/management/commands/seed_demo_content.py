import random
import secrets
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from polls.models import Option, Poll, Vote

User = get_user_model()

DEMO_USERNAMES = [
    "ayse_k",
    "mehmetc",
    "zeynepg",
    "burakk",
    "elifnaz",
    "kaganb",
    "selin34",
    "omerf",
    "iremyy",
    "denizc",
]

DEMO_POLLS = [
    {
        "question": "Bu akşam ne izlesek?",
        "description": "",
        "category": Poll.CATEGORY_EGLENCE,
        "options": ["Dizi", "Film", "Belgesel"],
        "weights": [0.65, 0.25, 0.10],
        "expires_in_hours": None,
    },
    {
        "question": "Kahve mi çay mı?",
        "description": "",
        "category": Poll.CATEGORY_YEMEK,
        "options": ["Kahve", "Çay"],
        "weights": [0.55, 0.45],
        "expires_in_hours": None,
    },
    {
        "question": "Yeni telefon hangi renk olsun?",
        "description": "",
        "category": Poll.CATEGORY_TEKNOLOJI,
        "options": ["Siyah", "Beyaz", "Mavi", "Yeşil"],
        "weights": [0.30, 0.28, 0.24, 0.18],
        "expires_in_hours": None,
    },
    {
        "question": "Hafta sonu hangi spor?",
        "description": "",
        "category": Poll.CATEGORY_SPOR,
        "options": ["Yüzme", "Koşu", "Bisiklet"],
        "weights": [0.50, 0.30, 0.20],
        "expires_in_hours": 48,
    },
    {
        "question": "İndirimde hangisini alsam?",
        "description": "",
        "category": Poll.CATEGORY_ALISVERIS,
        "options": ["Ayakkabı", "Çanta", "Saat", "Gözlük", "Kazak"],
        "weights": [0.24, 0.22, 0.20, 0.18, 0.16],
        "expires_in_hours": -48,
    },
]


class Command(BaseCommand):
    help = "Demo kullanıcılar, örnek anketler ve oylar oluşturur (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--only-new-polls",
            action="store_true",
            help="Sadece bu komutun oluşturduğu yeni anketlere oy ver; mevcut anketlere dokunma.",
        )
        parser.add_argument(
            "--password",
            help=(
                "Oluşturulan demo kullanıcılar için parola. Verilmezse her kullanıcı için "
                "ayrı, rastgele bir parola üretilir ve ekrana yazdırılır (repoda sabit bir "
                "parola tutmamak için — bkz. git geçmişindeki eski DEMO_PASSWORD sabiti)."
            ),
        )

    def handle(self, *args, **options):
        only_new_polls = options["only_new_polls"]
        fixed_password = options["password"]

        users = []
        for username in DEMO_USERNAMES:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"email": f"{username}@example.com"},
            )
            if created:
                password = fixed_password or secrets.token_urlsafe(12)
                user.set_password(password)
                user.save()
                self.stdout.write(f"Kullanıcı oluşturuldu: @{username} (parola: {password})")
            users.append(user)

        new_polls = []
        for index, spec in enumerate(DEMO_POLLS):
            poll, created = Poll.objects.get_or_create(
                question=spec["question"],
                defaults={
                    "author": users[index % len(users)],
                    "description": spec["description"],
                    "category": spec["category"],
                    "expires_at": (
                        timezone.now() + timedelta(hours=spec["expires_in_hours"])
                        if spec["expires_in_hours"] is not None
                        else None
                    ),
                },
            )
            if created:
                Option.objects.bulk_create(
                    Option(poll=poll, text=text, order=order)
                    for order, text in enumerate(spec["options"])
                )
                self.stdout.write(f"Anket oluşturuldu: {poll.question}")
            new_polls.append(poll)

        target_polls = new_polls if only_new_polls else Poll.objects.all()

        total_votes_created = 0
        with transaction.atomic():
            for poll in target_polls:
                options = list(poll.options.order_by("order"))
                if not options:
                    continue
                spec = next(
                    (s for s in DEMO_POLLS if s["question"] == poll.question), None
                )
                weights = spec["weights"] if spec else [1] * len(options)

                voters = list(users)
                random.shuffle(voters)
                for voter in voters:
                    if voter.id == poll.author_id:
                        continue
                    if random.random() > 0.85:
                        continue
                    if Vote.objects.filter(poll=poll, user=voter).exists():
                        continue
                    chosen = random.choices(options, weights=weights, k=1)[0]
                    vote = Vote.objects.create(poll=poll, option=chosen, user=voter)
                    backdated = timezone.now() - timedelta(
                        hours=random.randint(1, 96), minutes=random.randint(0, 59)
                    )
                    Vote.objects.filter(pk=vote.pk).update(created_at=backdated)
                    total_votes_created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Tamamlandı: {len(users)} kullanıcı, {len(new_polls)} yeni anket, "
                f"{total_votes_created} yeni oy."
            )
        )

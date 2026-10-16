import uuid

from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .models import Vote


@receiver(user_logged_in)
def migrate_guest_votes(sender, request, user, **kwargs):
    """Giriş anında (login veya kayıt sonrası otomatik login — ikisi de bu sinyali
    tetikler), o tarayıcının voter_id çerezine kayıtlı misafir oylarını kullanıcıya
    taşır. Kullanıcının o ankete zaten üye olarak oyu varsa (örn. başka bir
    cihazdan önceden oy vermiş), misafir oyu çakışma yaratmadan silinir.
    """
    voter_id = getattr(request, "voter_id", None)
    if not voter_id:
        return
    try:
        token = uuid.UUID(voter_id)
    except ValueError:
        return

    for vote in Vote.objects.filter(voter_token=token, user__isnull=True):
        if Vote.objects.filter(poll_id=vote.poll_id, user=user).exists():
            vote.delete()
        else:
            vote.user = user
            vote.voter_token = None
            vote.save(update_fields=["user", "voter_token"])

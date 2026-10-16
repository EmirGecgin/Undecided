from functools import wraps

from django.contrib import messages
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import redirect

DEFAULT_MESSAGE = "Çok fazla istek gönderdin, biraz bekleyip tekrar dene."


def _client_key(request):
    if request.user.is_authenticated:
        return f"user:{request.user.id}"
    return f"ip:{request.META.get('REMOTE_ADDR', 'unknown')}"


def _increment(cache_key, window_seconds):
    if cache.add(cache_key, 1, window_seconds):
        return 1
    try:
        return cache.incr(cache_key)
    except ValueError:
        cache.set(cache_key, 1, window_seconds)
        return 1


def rate_limit(key_prefix, limit, window_seconds, message=DEFAULT_MESSAGE):
    """Basit sabit pencereli hız sınırı: her istemci (giriş yapmışsa kullanıcı,
    değilse IP) için key_prefix başına window_seconds içinde en fazla limit istek.
    Redis gibi paylaşımlı bir önbellek olmadan (Vercel serverless'te her sıcak
    instance kendi belleğini tutar) sınır kesin değil ama yine de gerçek bir
    koruma katmanı — hiç sınır olmamasından çok daha iyi.
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            cache_key = f"ratelimit:{key_prefix}:{_client_key(request)}"
            count = _increment(cache_key, window_seconds)
            if count > limit:
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse({"ok": False, "error": message}, status=429)
                messages.error(request, message)
                referer = request.META.get("HTTP_REFERER")
                return redirect(referer or "polls:home")
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator

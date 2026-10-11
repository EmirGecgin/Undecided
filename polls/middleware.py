import uuid

from django.conf import settings

VOTER_COOKIE_NAME = "voter_id"
VOTER_COOKIE_MAX_AGE = 60 * 60 * 24 * 365  # 1 yıl


class VoterIDMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        voter_id = request.COOKIES.get(VOTER_COOKIE_NAME)
        is_new = not voter_id
        if is_new:
            voter_id = str(uuid.uuid4())
        request.voter_id = voter_id

        response = self.get_response(request)

        if is_new:
            response.set_cookie(
                VOTER_COOKIE_NAME,
                voter_id,
                max_age=VOTER_COOKIE_MAX_AGE,
                httponly=True,
                samesite="Lax",
                secure=not settings.DEBUG,
            )
        return response

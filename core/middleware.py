from django.utils import timezone


class LastSeenMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not request.user.is_authenticated:
            return response
        last = request.user.last_seen
        now = timezone.now()
        # write at most once per 60 seconds to avoid a DB hit on every request
        if not last or (now - last).total_seconds() > 60:
            request.user.__class__.objects.filter(pk=request.user.pk).update(last_seen=now)
        return response

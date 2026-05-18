from functools import wraps

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponseForbidden, JsonResponse


def _is_staff(user):
    return bool(user and user.is_authenticated and user.is_staff)


def staff_required_view(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), login_url=getattr(settings, "LOGIN_URL", None))
        if not _is_staff(request.user):
            return HttpResponseForbidden("You do not have permission to access reports.")
        return view_func(request, *args, **kwargs)

    return _wrapped


def staff_required_api(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not _is_staff(request.user):
            return JsonResponse({"detail": "Forbidden"}, status=403)
        return view_func(request, *args, **kwargs)

    return _wrapped

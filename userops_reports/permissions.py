from functools import wraps

from django.http import JsonResponse
from django.shortcuts import redirect


def _is_staff(user):
    return bool(user and user.is_authenticated and user.is_staff)


def staff_required_view(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not _is_staff(request.user):
            return redirect("/")
        return view_func(request, *args, **kwargs)

    return _wrapped


def staff_required_api(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not _is_staff(request.user):
            return JsonResponse({"detail": "Forbidden"}, status=403)
        return view_func(request, *args, **kwargs)

    return _wrapped

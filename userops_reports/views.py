import logging

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from userops_reports.db import ReportQueryError
from userops_reports.permissions import staff_required_api, staff_required_view
from userops_reports.services.asm_reports import get_asm_dealers, get_asm_overview, get_asms, get_rsms
from userops_reports.services.cluster_reports import get_asm_performance, get_cluster_performance, get_clusters
from userops_reports.services.course_reports import (
    get_course_details,
    get_course_learners,
    get_courses,
    get_courses_overview,
)
from userops_reports.services.user_reports import get_user_details_by_id, get_user_details_by_username, search_users

logger = logging.getLogger(__name__)


def _safe_json(handler):
    try:
        return JsonResponse(handler())
    except ReportQueryError:
        return JsonResponse({"detail": "Unable to load report data."}, status=500)


@require_GET
@staff_required_view
def progress_overview(request):
    return render(request, "userops_reports/progress_overview.html")


@require_GET
@staff_required_api
def api_clusters(request):
    return _safe_json(get_clusters)


@require_GET
@staff_required_api
def api_cluster_performance(request):
    return _safe_json(get_cluster_performance)


@require_GET
@staff_required_api
def api_asms(request):
    return _safe_json(get_asms)


@require_GET
@staff_required_api
def api_rsms(request):
    return _safe_json(get_rsms)


@require_GET
@staff_required_api
def api_asm_performance(request, cluster):
    return _safe_json(lambda: get_asm_performance(cluster))


@require_GET
@staff_required_api
def api_asm_dealers(request, asm):
    return _safe_json(lambda: get_asm_dealers(asm))


@require_GET
@staff_required_api
def api_asm_overview(request):
    return _safe_json(lambda: {"asms": get_asm_overview()})


@require_GET
@staff_required_api
def api_courses(request):
    return _safe_json(get_courses)


@require_GET
@staff_required_api
def api_courses_overview(request):
    return _safe_json(get_courses_overview)


@require_GET
@staff_required_api
def api_course(request, course_id):
    def _handler():
        payload = get_course_details(course_id)
        if payload is None:
            return {"detail": "Course not found"}
        return payload

    response = _safe_json(_handler)
    if response.content == b'{"detail": "Course not found"}':
        response.status_code = 404
    return response


@require_GET
@staff_required_api
def api_course_learners(request, course_id):
    return _safe_json(lambda: get_course_learners(course_id))


@require_GET
@staff_required_api
def api_search(request):
    query = request.GET.get("query", "").strip()
    if len(query) < 2:
        return JsonResponse({"users": []})
    return _safe_json(lambda: search_users(query))


@require_GET
@staff_required_api
def api_user(request, username):
    def _handler():
        payload = get_user_details_by_username(username)
        if payload is None:
            return {"detail": "User not found"}
        return payload

    response = _safe_json(_handler)
    if response.content == b'{"detail": "User not found"}':
        response.status_code = 404
    return response


@require_GET
@staff_required_api
def api_user_by_id(request, user_id):
    def _handler():
        payload = get_user_details_by_id(user_id)
        if payload is None:
            return {"detail": "User not found"}
        return payload

    response = _safe_json(_handler)
    if response.content == b'{"detail": "User not found"}':
        response.status_code = 404
    return response


@require_GET
@staff_required_api
def api_dashboard_metrics(request):
    def _handler():
        cp = get_cluster_performance()
        asms = get_asms().get("asms", [])
        totals = cp.get("totals", {})
        return {
            "total_clusters": len(cp.get("clusters", [])),
            "total_asms": len(asms),
            "total_dealers": totals.get("total_users", 0),
            "total_assigned_courses": totals.get("assigned_courses", 0),
            "total_completed": totals.get("completed_courses", 0),
            "total_in_progress": totals.get("in_progress", 0),
            "total_not_started": totals.get("not_started", 0),
            "overall_progress": totals.get("avg_progress", 0),
            "clusters": cp.get("clusters", []),
        }

    return _safe_json(_handler)

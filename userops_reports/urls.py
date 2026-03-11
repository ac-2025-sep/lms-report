from django.urls import path
from userops_reports import views

app_name = "userops_reports"

urlpatterns = [
    path("progress_overview", views.progress_overview, name="progress_overview"),
    path("api/clusters", views.api_clusters, name="api_clusters"),
    path("api/cluster-performance", views.api_cluster_performance, name="api_cluster_performance"),
    path("api/asms", views.api_asms, name="api_asms"),
    path("api/rsms", views.api_rsms, name="api_rsms"),
    path("api/asm-performance/<str:cluster>", views.api_asm_performance, name="api_asm_performance"),
    path("api/asm-dealers/<str:asm>", views.api_asm_dealers, name="api_asm_dealers"),
    path("api/asm-overview", views.api_asm_overview, name="api_asm_overview"),
    path("api/courses", views.api_courses, name="api_courses"),
    path("api/courses/overview", views.api_courses_overview, name="api_courses_overview"),
    path("api/dashboard-metrics", views.api_dashboard_metrics, name="api_dashboard_metrics"),
    path("api/course/<str:course_id>", views.api_course, name="api_course"),
    path("api/courses/<str:course_id>", views.api_course, name="api_course_legacy"),
    path("api/course/<str:course_id>/learners", views.api_course_learners, name="api_course_learners"),
    path("api/courses/<str:course_id>/learners", views.api_course_learners, name="api_course_learners_legacy"),
    path("api/search", views.api_search, name="api_search"),
    path("api/user/<str:username>", views.api_user, name="api_user"),
    path("api/user-id/<int:user_id>", views.api_user_by_id, name="api_user_by_id"),
]

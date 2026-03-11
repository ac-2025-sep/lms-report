from django.urls import path

from userops_reports import views

app_name = "userops_reports"

urlpatterns = [
    path("userops/progress_overview", views.progress_overview, name="progress_overview"),
    path("userops/api/clusters", views.api_clusters, name="api_clusters"),
    path("userops/api/cluster-performance", views.api_cluster_performance, name="api_cluster_performance"),
    path("userops/api/asms", views.api_asms, name="api_asms"),
    path("userops/api/rsms", views.api_rsms, name="api_rsms"),
    path("userops/api/asm-performance/<str:cluster>", views.api_asm_performance, name="api_asm_performance"),
    path("userops/api/asm-dealers/<str:asm>", views.api_asm_dealers, name="api_asm_dealers"),
    path("userops/api/asm-overview", views.api_asm_overview, name="api_asm_overview"),
    path("userops/api/courses", views.api_courses, name="api_courses"),
    path("userops/api/courses/overview", views.api_courses_overview, name="api_courses_overview"),
    path("userops/api/dashboard-metrics", views.api_dashboard_metrics, name="api_dashboard_metrics"),
    path("userops/api/course/<str:course_id>", views.api_course, name="api_course"),
    path("userops/api/courses/<str:course_id>", views.api_course, name="api_course_legacy"),
    path("userops/api/course/<str:course_id>/learners", views.api_course_learners, name="api_course_learners"),
    path("userops/api/courses/<str:course_id>/learners", views.api_course_learners, name="api_course_learners_legacy"),
    path("userops/api/search", views.api_search, name="api_search"),
    path("userops/api/user/<str:username>", views.api_user, name="api_user"),
    path("userops/api/user-id/<int:user_id>", views.api_user_by_id, name="api_user_by_id"),
]

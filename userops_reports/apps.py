from django.apps import AppConfig

try:
    from edx_django_utils.plugins import PluginURLs
    from openedx.core.djangoapps.plugins.constants import ProjectType
except Exception:  # pragma: no cover - available inside Open edX runtime
    _PLUGIN_APP = None
else:
    _PLUGIN_APP = {
        PluginURLs.CONFIG: {
            ProjectType.LMS: {
                PluginURLs.NAMESPACE: "userops_reports",
                PluginURLs.REGEX: r"^userops/",
                PluginURLs.RELATIVE_PATH: "urls",
            }
        }
    }


class UseropsReportsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "userops_reports"
    verbose_name = "UserOps Reports"

    if _PLUGIN_APP:
        plugin_app = _PLUGIN_APP

from tutor import hooks


hooks.Filters.ENV_PATCHES.add_item(
    (
        "openedx-dockerfile-post-python-requirements",
        """
# LMS reports Django app
RUN pip install --no-cache-dir git+https://github.com/ac-2025-sep/lms-report.git
""",
    )
)

hooks.Filters.ENV_PATCHES.add_item(
    (
        "openedx-lms-common-settings",
        """
# LMS reports
if "userops_reports" not in INSTALLED_APPS:
    INSTALLED_APPS.append("userops_reports")
""",
    )
)

try:
    from tutormfe.hooks import PLUGIN_SLOTS
except ImportError:  # pragma: no cover - tutormfe is present in MFE-enabled Tutor installs
    PLUGIN_SLOTS = None

if PLUGIN_SLOTS:
    PLUGIN_SLOTS.add_items(
        [
            (
                "authoring",
                "org.openedx.frontend.layout.studio_header_search_button_slot.v1",
                """
                {
                  op: PLUGIN_OPERATIONS.Hide,
                  widgetId: 'studio-admin-buttons',
                }
                """,
            ),
            (
                "authoring",
                "org.openedx.frontend.layout.studio_header_search_button_slot.v1",
                r"""
                {
                  op: PLUGIN_OPERATIONS.Insert,
                  widget: {
                    id: 'studio-internal-admin-buttons',
                    type: DIRECT_PLUGIN,
                    RenderWidget: () => {
                      const base = window.location.origin
                        .replace('apps.', '')
                        .replace('studio.', '')
                        .replace(/\/$/, '');

                      return (
                        <div className="d-flex align-items-center ms-2" style={{ gap: '10px' }}>
                          <a className="btn btn-outline-primary" href={`${base}/userops/progress_overview`}>
                            Report Dashboard
                          </a>
                          <a className="btn btn-outline-primary" href={`${base}/userops/`}>
                            Bulk Enroll
                          </a>
                        </div>
                      );
                    },
                  },
                }
                """,
            ),
        ]
    )

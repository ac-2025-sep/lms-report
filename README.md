# lms-report

`lms-report` is a **reusable Django app package** for Open edX LMS UserOps reporting.

It is no longer a standalone FastAPI runtime.

## What this package provides

- Dashboard page for progress overview.
- Staff-only JSON API endpoints used by the dashboard.
- App-scoped templates and static assets ready for Django packaging.
- SQL report services executed through Django DB connection.

## Intended LMS routes

When included under `userops/`:

- `/userops/progress_overview`
- `/userops/api/...`

## Package/app structure

```text
userops_reports/
  __init__.py
  apps.py
  urls.py
  views.py
  permissions.py
  db.py
  services/
    cluster_reports.py
    asm_reports.py
    course_reports.py
    user_reports.py
  templates/
    userops_reports/
      progress_overview.html
  static/
    userops_reports/
      css/dashboard.css
      js/dashboard.js
```

## Integration in Open edX LMS

1. Install this package into the LMS Python environment.
2. Add `userops_reports` to `INSTALLED_APPS`.
3. Include URLs under `userops/`:

```python
from django.urls import include, path

urlpatterns += [
    path("userops/", include("userops_reports.urls")),
]
```

See `integration_notes.md` for detailed integration guidance and plugin wiring notes.

## Static assets

Dashboard assets are located in app static paths:

- `userops_reports/static/userops_reports/js/dashboard.js`
- `userops_reports/static/userops_reports/css/dashboard.css`

Templates reference these assets with `{% static %}` tags.

If you see static 404s, validate staticfiles collection/serving in LMS. This is independent from `/userops/` URL ownership.

## Database access

Database access is Django-native:

- `userops_reports/db.py` uses `django.db.connection`.
- Shared helpers:
  - `fetch_all_dict(sql, params=None)`
  - `fetch_one_dict(sql, params=None)`

No standalone DB credentials are managed by this package.

## Permissions

UI and APIs are guarded by staff checks (`request.user.is_staff`) in `userops_reports/permissions.py`.

## Legacy FastAPI files

Historical FastAPI files remain only as explicit deprecation stubs:

- `main.py`
- `report_router.py`
- `router4.py`
- `router5.py`

They are not part of the Django runtime.

## Schema assumptions / caveats

Current report SQL assumes Open edX LMS tables and `auth_userprofile.meta` JSON fields for UserOps hierarchy data (`cluster`, `asm`, `rsm`, dealer/champion metadata).

If your deployment schema/custom fields differ, adjust SQL in `userops_reports/services/*.py`.

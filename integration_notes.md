# Integration notes for Open edX LMS

This repository provides a reusable Django app package named **`userops_reports`**.

## Intended routes

When included correctly, the app exposes:

- UI page: **`/userops/progress_overview`**
- APIs: **`/userops/api/...`**

## Required URL include pattern

Include this app under `userops/` in LMS URL config:

```python
from django.urls import include, path

urlpatterns += [
    path("userops/", include("userops_reports.urls")),
]
```

### Why this include pattern

`userops_reports/urls.py` is intentionally **prefix-free** and declares routes such as:

- `progress_overview`
- `api/clusters`
- `api/cluster-performance`
- `api/asms`
- `api/rsms`
- ...

Because another LMS app already owns the `/userops/` namespace, this package must be mounted under that prefix to avoid duplicate prefixes like `/userops/userops/...`.

If you include this app at `""` instead, endpoints will be exposed at `/progress_overview` and `/api/...`, which is not the intended integration.

## INSTALLED_APPS

Add the app to LMS settings:

```python
INSTALLED_APPS += [
    "userops_reports",
]
```

## Static and template behavior

Static assets are shipped inside the app:

- `userops_reports/static/userops_reports/js/dashboard.js`
- `userops_reports/static/userops_reports/css/dashboard.css`

Template:

- `userops_reports/templates/userops_reports/progress_overview.html`

The template uses Django `{% static %}` tags, so static asset URLs are generated as:

- `/static/userops_reports/js/dashboard.js`
- `/static/userops_reports/css/dashboard.css`

### Important: `/static/...` vs `/userops/...`

These are separate concerns:

- `/userops/...` is handled by Django URL routing.
- `/static/...` is handled by Django staticfiles collection/serving.

So a `/static/userops_reports/js/dashboard.js` 404 is **not caused** by `/userops/` ownership by another app. It is typically caused by staticfiles configuration/collection or missing packaged static files.

## Database access model

This app no longer manages standalone DB credentials.

- Uses Django/Open edX runtime database settings.
- SQL execution runs through `django.db.connection` via helpers in `userops_reports/db.py`.
- No `mysql.connector`, no embedded host/user/password defaults.

This package must run inside the LMS Django runtime where Open edX DB settings are already configured.

## Example wiring from another Tutor/Open edX plugin

In your separate plugin repo (not in this package), apply LMS patches/hooks equivalent to:

```python
# settings patch
INSTALLED_APPS += ["userops_reports"]

# urls patch
from django.urls import include, path
urlpatterns += [
    path("userops/", include("userops_reports.urls")),
]
```

Then rebuild/restart LMS and run static collection according to your Tutor/Open edX workflow.

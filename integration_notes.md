# Integration notes for Open edX LMS

This repository now ships a reusable Django app package named **`userops_reports`**.

## 1) Add to INSTALLED_APPS

```python
INSTALLED_APPS += [
    "userops_reports",
]
```

## 2) Include URLs in LMS routing

```python
from django.urls import include, path

urlpatterns += [
    path("", include("userops_reports.urls")),
]
```

This exposes:
- Page: `/userops/progress_overview`
- APIs: `/userops/api/...`

## 3) Intended final route

Primary UI route: **`/userops/progress_overview`**

## 4) Static/templates

- Template: `userops_reports/templates/userops_reports/progress_overview.html`
- Static:
  - `userops_reports/static/userops_reports/css/dashboard.css`
  - `userops_reports/static/userops_reports/js/dashboard.js`

Ensure your LMS static pipeline collects app static files.

## 5) Permissions model

All page/API views use a **staff-only access guard** (`request.user.is_staff`).

## 6) Open edX assumptions

The report logic assumes:
- Open edX LMS DB schema availability for enrollment, certificate, grade, and module tables.
- `auth_userprofile.meta` contains hierarchy fields in JSON under `$.org.*`, including:
  - `cluster`, `asm`, `rsm`
  - `dealer_name`, `dealer_id`
  - `champion_name`, `champion_mobile`
  - related geo/category fields

If your deployment differs, adjust SQL in `userops_reports/services/*.py`.

## 7) Example from another plugin repo (reference only)

You can wire this package from your own Tutor/Open edX plugin repo by adding app + URL includes in the LMS Django settings/URL extension hooks used by that plugin.

> This repository intentionally does **not** implement Tutor hook patches directly.

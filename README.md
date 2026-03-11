# lms-report

`lms-report` is now a **reusable Django app package** that provides a UserOps reporting dashboard intended for Open edX LMS deployments.

## What this repository now contains

- Django app package: `userops_reports`
- Dashboard page intended route: `/userops/progress_overview`
- JSON API endpoints under: `/userops/api/...`
- Template and static assets extracted from the previous `asm_dashboard05.html`
- SQL/report logic moved into service modules (thin views pattern)

## App layout

- `userops_reports/apps.py` – app config
- `userops_reports/urls.py` – page + API URL map
- `userops_reports/views.py` – Django views (HTML + JSON)
- `userops_reports/permissions.py` – staff-only guard helpers
- `userops_reports/db.py` – shared SQL execution helper via Django DB connection
- `userops_reports/services/*` – query/report modules
- `userops_reports/templates/userops_reports/progress_overview.html`
- `userops_reports/static/userops_reports/css/dashboard.css`
- `userops_reports/static/userops_reports/js/dashboard.js`

## Local development

This repository is packaged as a Django app, not a standalone server.

1. Install dependencies:

```bash
pip install -e .
```

2. In a host Django project (or Open edX LMS shell), add `userops_reports` to `INSTALLED_APPS`.
3. Include `userops_reports.urls` in URL routing.
4. Ensure DB tables used in SQL exist in your Open edX LMS DB.

## Open edX integration intent

See `integration_notes.md` for wiring snippets and assumptions.

## Refactor notes

Replaced/obsoleted FastAPI runtime files:
- `main.py`
- `report_router.py`
- `router4.py`
- `router5.py`

These now only contain deprecation notes.

## Known caveats / TODO

- SQL metrics are preserved close to previous behavior and rely on Open edX schema plus `auth_userprofile.meta` JSON hierarchy (`cluster`, `asm`, `rsm`, dealer/champion fields).
- Some grade/progress semantics may vary by Open edX distribution and custom data population.
- Validate query performance and indexing in production-sized datasets.

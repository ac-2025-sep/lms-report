# lms-report

`lms-report` is an Open edX/Tutor plugin package for the UserOps LMS report dashboard.

It replaces the external FastAPI report URL with an internal LMS page:

- Report UI: `/userops/progress_overview`
- Report APIs: `/userops/api/...`

## Architecture

The previous standalone workspace at `/home/ubuntu/lms_report` is a FastAPI/Jinja app. Its current report UI is served from `/lmsreport/reportui6`, using `asm_dashboard06uifix_sfl_lms.html` and API logic in `router6forsfl.py`.

This repository keeps that behavior inside Open edX as:

- `userops_reports`: Django app installed into the LMS runtime.
- `userops_reports.urls`: internal LMS URL/API routes mounted at `/userops/`.
- `userops_reports.services`: SQL report services using `django.db.connection`.
- `userops_reports/templates` and `userops_reports/static`: packaged dashboard UI assets.
- `lms_report_tutor`: Tutor plugin entrypoint and Tutor/MFE patches.

The legacy FastAPI files in this repository are retained only as historical reference/deprecation stubs.

## Permissions

- Anonymous users are redirected to LMS login before viewing the report page.
- Authenticated non-staff users are blocked.
- Staff/admin users can access the report UI and APIs.
- API endpoints return JSON `403` for unauthorized users.

The initial policy is intentionally staff-only via `request.user.is_staff`.

## Report Logic

The Django services mirror the current `/reportui6` backend behavior from `router6forsfl.py`:

- Progress and completion are primarily calculated from `grades_persistentcoursegrade.percent_grade`.
- Completed: `percent_grade >= 1.0`.
- In progress: `0 < percent_grade < 1.0`.
- Not started: missing or zero grade.
- Course learner details include grade, letter grade, completion status, enrollment dates, module counts, and dealer hierarchy metadata.
- User details include dealer metadata, course summary counts, and enrolled course rows for the user modal.

The report SQL assumes standard Open edX LMS tables plus UserOps hierarchy data in `auth_userprofile.meta` JSON fields such as `cluster`, `asm`, `rsm`, `dealer_name`, `dealer_id`, `champion_name`, `brand`, `role`, and `department`.

## Install and Enable

You will run these from the Tutor host.

```bash
pip install -e /home/ubuntu/edxtutor/lms-report
tutor plugins enable lms-report
tutor config save
tutor images build openedx
tutor local restart lms cms
```

For a fresh environment, use your normal `tutor local launch` flow after enabling the plugin.

Important: the Tutor Dockerfile patch installs this package into the Open edX image from:

```text
git+https://github.com/ac-2025-sep/lms-report.git
```

Push the desired commit before rebuilding the openedx image, or adjust `lms_report_tutor/plugin.py` to point at your deployment branch/tag.

## Disable

```bash
tutor plugins disable lms-report
tutor config save
tutor local restart lms cms
```

## Verification Checklist

- LMS starts successfully after enabling the plugin.
- `/userops/progress_overview` opens for staff/admin users.
- Logged-out users are redirected through LMS login.
- Normal learners cannot access the report page.
- Normal learners receive JSON `403` from `/userops/api/...`.
- These staff API calls return dashboard-compatible payloads:
  - `/userops/api/dashboard-metrics`
  - `/userops/api/courses/overview`
  - `/userops/api/course/<course_id>`
  - `/userops/api/course/<course_id>/learners`
  - `/userops/api/search?query=<term>`
  - `/userops/api/user-id/<user_id>`
- The Studio header “Report Dashboard” button opens `/userops/progress_overview`, not `https://demodms.staqo.com/lmsreport/reportui6`.
- After the internal page is validated, the old external report link can be removed from any remaining custom Tutor/MFE plugins.

## Local Static Checks

```bash
python3 -m compileall userops_reports lms_report_tutor
node --check userops_reports/static/userops_reports/js/dashboard.js
python3 - <<'PY'
import tomllib
with open("pyproject.toml", "rb") as f:
    data = tomllib.load(f)
print(data["project"]["entry-points"]["tutor.plugin.v1"])
PY
```

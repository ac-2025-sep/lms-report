"""Obsolete FastAPI API router.

Primary logic from this module was refactored into:
- `userops_reports/services/cluster_reports.py`
- `userops_reports/services/asm_reports.py`
- `userops_reports/services/course_reports.py`
- `userops_reports/services/user_reports.py`

The Django HTTP layer now lives in `userops_reports/views.py` with routes in
`userops_reports/urls.py`.
"""

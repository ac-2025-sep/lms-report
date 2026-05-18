from userops_reports.db import fetch_all_dict, fetch_one_dict
from userops_reports.services.common import as_float, as_int, date_filter_clause, iso, meta_value, valid_meta


def get_courses():
    rows = fetch_all_dict("""
        SELECT co.id as course_id, co.display_name as name
        FROM course_overviews_courseoverview co
        ORDER BY co.display_name
    """)
    return {"courses": [{"id": r["course_id"], "name": r["name"], "display_name": r["name"]} for r in rows]}


def get_courses_overview(date_range="all", start_date=None, end_date=None):
    date_clause, params = date_filter_clause("sce.created", date_range, start_date, end_date)
    rows = fetch_all_dict(f"""
        SELECT
            co.id AS course_id,
            co.display_name AS course_name,
            co.start,
            co.end,
            co.org,
            COUNT(DISTINCT sce.user_id) AS total_enrollments,
            COUNT(DISTINCT gc.id) AS certificates_issued,
            COUNT(DISTINCT CASE WHEN gpcg.passed_timestamp IS NOT NULL THEN sce.user_id END) AS passed_count,
            COUNT(DISTINCT CASE WHEN gpcg.percent_grade > 0 AND gpcg.passed_timestamp IS NULL THEN sce.user_id END) AS in_progress_count,
            COALESCE(ROUND(AVG(COALESCE(gpcg.percent_grade, 0)) * 100, 2), 0) AS avg_grade,
            MAX(gpcg.modified) AS last_activity
        FROM course_overviews_courseoverview co
        LEFT JOIN student_courseenrollment sce ON co.id = sce.course_id AND sce.is_active = 1{date_clause}
        LEFT JOIN auth_userprofile up ON sce.user_id = up.user_id
        LEFT JOIN certificates_generatedcertificate gc ON sce.user_id = gc.user_id
            AND sce.course_id = gc.course_id AND gc.status = 'downloadable'
        LEFT JOIN grades_persistentcoursegrade gpcg ON sce.course_id = gpcg.course_id
            AND sce.user_id = gpcg.user_id
        WHERE {valid_meta("up")}
        GROUP BY co.id, co.display_name, co.start, co.end, co.org
        ORDER BY co.display_name
    """, tuple(params))
    courses = []
    for row in rows:
        avg_grade = as_float(row.get("avg_grade"))
        courses.append({
            "course_id": row["course_id"],
            "course_name": row["course_name"],
            "total_enrollments": as_int(row.get("total_enrollments")),
            "certificates_issued": as_int(row.get("certificates_issued")),
            "active_learners": as_int(row.get("passed_count")),
            "passed_count": as_int(row.get("passed_count")),
            "in_progress_count": as_int(row.get("in_progress_count")),
            "avg_grade": avg_grade,
            "avg_completion": avg_grade,
            "last_activity": iso(row.get("last_activity")),
        })
    return {"courses": courses}


def get_course_details(course_id, date_range="all", start_date=None, end_date=None):
    course = fetch_one_dict("""
        SELECT id AS course_id, display_name AS course_name, start, end, org, modified
        FROM course_overviews_courseoverview
        WHERE id = %s
    """, (course_id,))
    if not course:
        return None

    date_clause, date_params = date_filter_clause("sce.created", date_range, start_date, end_date)
    stats = fetch_one_dict(f"""
        SELECT
            COUNT(DISTINCT sce.user_id) AS total_enrollments,
            COUNT(DISTINCT gc.id) AS certificates_issued,
            COUNT(DISTINCT CASE WHEN gpcg.passed_timestamp IS NOT NULL THEN sce.user_id END) AS passed_count,
            COUNT(DISTINCT CASE WHEN gpcg.percent_grade > 0 AND gpcg.passed_timestamp IS NULL THEN sce.user_id END) AS in_progress_count,
            COUNT(DISTINCT CASE
                WHEN gpcg.passed_timestamp IS NULL
                  AND (gpcg.percent_grade IS NULL OR gpcg.percent_grade = 0)
                  AND sm.student_id IS NOT NULL
                THEN sce.user_id END) AS started_count,
            COUNT(DISTINCT CASE
                WHEN gpcg.passed_timestamp IS NULL
                  AND (gpcg.percent_grade IS NULL OR gpcg.percent_grade = 0)
                  AND sm.student_id IS NULL
                THEN sce.user_id END) AS not_started_count,
            COALESCE(ROUND(AVG(COALESCE(gpcg.percent_grade, 0)) * 100, 2), 0) AS avg_grade,
            MAX(gpcg.modified) AS last_activity
        FROM student_courseenrollment sce
        LEFT JOIN auth_userprofile up ON sce.user_id = up.user_id
        LEFT JOIN certificates_generatedcertificate gc ON sce.user_id = gc.user_id
            AND sce.course_id = gc.course_id AND gc.status = 'downloadable'
        LEFT JOIN grades_persistentcoursegrade gpcg ON sce.course_id = gpcg.course_id
            AND sce.user_id = gpcg.user_id
        LEFT JOIN (
            SELECT DISTINCT student_id, course_id
            FROM courseware_studentmodule
        ) sm ON sce.user_id = sm.student_id AND sce.course_id = sm.course_id
        WHERE sce.course_id = %s AND sce.is_active = 1{date_clause}
          AND {valid_meta("up")}
    """, tuple([course_id] + date_params)) or {}

    passed = as_int(stats.get("passed_count"))
    in_progress = as_int(stats.get("in_progress_count"))
    started = as_int(stats.get("started_count"))
    if passed:
        completion_status = "completed"
    elif in_progress:
        completion_status = "in_progress"
    elif started:
        completion_status = "started"
    else:
        completion_status = "not_started"

    avg_grade = as_float(stats.get("avg_grade"))
    return {
        "course_id": course["course_id"],
        "course_name": course.get("course_name") or course["course_id"],
        "start_date": iso(course.get("start")),
        "end_date": iso(course.get("end")),
        "org": course.get("org"),
        "total_enrollments": as_int(stats.get("total_enrollments")),
        "certificates_issued": as_int(stats.get("certificates_issued")),
        "passed_count": passed,
        "in_progress_count": in_progress,
        "started_count": started,
        "not_started_count": as_int(stats.get("not_started_count")),
        "avg_grade": avg_grade,
        "avg_completion": avg_grade,
        "last_activity": iso(stats.get("last_activity")),
        "completion_status": completion_status,
    }


def get_course_learners(course_id, date_range="all", start_date=None, end_date=None):
    date_clause, date_params = date_filter_clause("sce.created", date_range, start_date, end_date)
    rows = fetch_all_dict(f"""
        SELECT
            sce.course_id,
            au.id AS user_id,
            au.username,
            au.email,
            COALESCE(
                {meta_value("up", "name")},
                {meta_value("up", "dealer_name")},
                au.username
            ) as name,
            {meta_value("up", "dealer_name")} as dealer_name,
            {meta_value("up", "dealer_id")} as dealer_id,
            {meta_value("up", "city")} as city,
            {meta_value("up", "state")} as state,
            {meta_value("up", "dealer_category")} as dealer_category,
            {meta_value("up", "cluster")} as cluster,
            {meta_value("up", "asm")} as asm,
            {meta_value("up", "rsm")} as rsm,
            {meta_value("up", "role")} as role,
            {meta_value("up", "department")} as department,
            {meta_value("up", "brand")} as brand,
            ROUND(gpcg.percent_grade * 100, 2) AS percent_grade,
            gpcg.letter_grade,
            CASE WHEN gpcg.passed_timestamp IS NOT NULL THEN 'Passed' ELSE 'Not Passed' END AS completion_status,
            gpcg.passed_timestamp,
            gpcg.modified AS grade_last_updated,
            sce.mode as enrollment_mode,
            sce.created as enrollment_date
        FROM student_courseenrollment AS sce
        JOIN auth_user AS au ON au.id = sce.user_id
        JOIN auth_userprofile AS up ON au.id = up.user_id
        LEFT JOIN grades_persistentcoursegrade AS gpcg ON gpcg.course_id = sce.course_id
            AND gpcg.user_id = sce.user_id
        WHERE sce.course_id = %s AND sce.is_active = 1{date_clause}
          AND {valid_meta("up")}
        ORDER BY
            CASE WHEN gpcg.passed_timestamp IS NOT NULL THEN 1 WHEN gpcg.percent_grade > 0 THEN 2 ELSE 3 END,
            gpcg.percent_grade DESC
    """, tuple([course_id] + date_params))
    learners = []
    for row in rows:
        percent_grade = as_float(row.get("percent_grade"))
        completed_modules = 0
        status = "completed" if row.get("completion_status") == "Passed" else "in_progress" if percent_grade > 0 else "not_started"
        learners.append({
            "user_id": row["user_id"],
            "username": row["username"],
            "email": row["email"],
            "name": row.get("name") or row["username"],
            "dealer_name": row.get("dealer_name") or row["username"],
            "dealer_id": row.get("dealer_id") or "N/A",
            "city": row.get("city") or "N/A",
            "state": row.get("state") or "N/A",
            "dealer_category": row.get("dealer_category") or "N/A",
            "cluster": row.get("cluster") or "Unassigned",
            "asm": row.get("asm") or "Unassigned",
            "rsm": row.get("rsm") or "Unassigned",
            "role": row.get("role") or "Champion",
            "department": row.get("department") or "N/A",
            "brand": row.get("brand") or "N/A",
            "percent_grade": percent_grade,
            "grade": percent_grade,
            "letter_grade": row.get("letter_grade") or "N/A",
            "completion_status": row.get("completion_status") or "Not Passed",
            "passed_timestamp": iso(row.get("passed_timestamp")),
            "grade_last_updated": iso(row.get("grade_last_updated")),
            "enrollment_mode": row.get("enrollment_mode"),
            "enrollment_date": iso(row.get("enrollment_date")),
            "completed_modules": completed_modules,
            "in_progress_modules": 0,
            "total_modules": 0,
            "status": status,
        })
    return {"learners": learners}

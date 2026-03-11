from userops_reports.db import execute_query


def get_courses():
    rows = execute_query("""
        SELECT co.id as course_id, co.display_name as name
        FROM course_overviews_courseoverview co
        ORDER BY co.display_name
    """)
    return {"courses": [{"id": r["course_id"], "name": r["name"], "display_name": r["name"]} for r in rows]}


def get_courses_overview():
    rows = execute_query("""
        SELECT co.id AS course_id, co.display_name AS course_name,
            COUNT(DISTINCT sce.user_id) AS total_enrollments,
            COUNT(DISTINCT gc.id) AS certificates_issued,
            COUNT(DISTINCT CASE WHEN gpcg.passed_timestamp IS NOT NULL THEN sce.user_id END) AS passed_count,
            COALESCE(ROUND(AVG(COALESCE(gpcg.percent_grade, 0)) * 100, 2), 0) AS avg_grade,
            MAX(gpcg.modified) AS last_activity
        FROM course_overviews_courseoverview co
        LEFT JOIN student_courseenrollment sce ON co.id = sce.course_id AND sce.is_active = 1
        LEFT JOIN auth_userprofile up ON sce.user_id = up.user_id
        LEFT JOIN certificates_generatedcertificate gc ON sce.user_id = gc.user_id AND sce.course_id = gc.course_id AND gc.status = 'downloadable'
        LEFT JOIN grades_persistentcoursegrade gpcg ON sce.course_id = gpcg.course_id AND sce.user_id = gpcg.user_id
        WHERE up.meta IS NOT NULL AND up.meta != '' AND up.meta != 'null' AND JSON_VALID(up.meta) = 1
        GROUP BY co.id, co.display_name
        ORDER BY co.display_name
    """)
    courses = []
    for row in rows:
        courses.append({
            "course_id": row["course_id"], "course_name": row["course_name"],
            "total_enrollments": int(row.get("total_enrollments") or 0),
            "certificates_issued": int(row.get("certificates_issued") or 0),
            "active_learners": int(row.get("passed_count") or 0),
            "avg_completion": float(row.get("avg_grade") or 0),
            "last_activity": row["last_activity"].isoformat() if row.get("last_activity") else None,
        })
    return {"courses": courses}


def get_course_details(course_id):
    rows = execute_query("""
        SELECT co.id AS course_id, co.display_name AS course_name,
            COUNT(DISTINCT sce.user_id) AS total_enrollments,
            COUNT(DISTINCT gc.id) AS certificates_issued,
            COUNT(DISTINCT CASE WHEN gpcg.passed_timestamp IS NOT NULL THEN sce.user_id END) AS passed_count,
            COUNT(DISTINCT CASE WHEN gpcg.percent_grade > 0 AND gpcg.passed_timestamp IS NULL THEN sce.user_id END) AS in_progress_count,
            COALESCE(ROUND(AVG(COALESCE(gpcg.percent_grade, 0)) * 100, 2), 0) AS avg_grade,
            MAX(gpcg.modified) AS last_activity
        FROM course_overviews_courseoverview co
        LEFT JOIN student_courseenrollment sce ON co.id = sce.course_id AND sce.is_active = 1
        LEFT JOIN certificates_generatedcertificate gc ON sce.user_id = gc.user_id AND sce.course_id = gc.course_id AND gc.status = 'downloadable'
        LEFT JOIN grades_persistentcoursegrade gpcg ON sce.course_id = gpcg.course_id AND sce.user_id = gpcg.user_id
        WHERE co.id = %s
        GROUP BY co.id, co.display_name
    """, (course_id,))
    if not rows:
        return None
    row = rows[0]
    return {
        "course_id": row["course_id"], "course_name": row["course_name"],
        "total_enrollments": int(row.get("total_enrollments") or 0),
        "certificates_issued": int(row.get("certificates_issued") or 0),
        "passed_count": int(row.get("passed_count") or 0),
        "in_progress_count": int(row.get("in_progress_count") or 0),
        "avg_completion": float(row.get("avg_grade") or 0),
        "last_activity": row["last_activity"].isoformat() if row.get("last_activity") else None,
    }


def get_course_learners(course_id):
    rows = execute_query("""
        SELECT u.id as user_id, u.username, u.email,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.dealer_name')) as dealer_name,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.cluster')) as cluster,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.asm')) as asm,
            ROUND(gpcg.percent_grade * 100, 1) as grade,
            CASE WHEN gc.id IS NOT NULL THEN 'completed'
                 WHEN gpcg.percent_grade > 0 THEN 'in_progress'
                 ELSE 'not_started' END as status
        FROM student_courseenrollment sce
        JOIN auth_user u ON sce.user_id = u.id
        JOIN auth_userprofile up ON u.id = up.user_id
        LEFT JOIN certificates_generatedcertificate gc ON sce.user_id = gc.user_id AND sce.course_id = gc.course_id AND gc.status = 'downloadable'
        LEFT JOIN grades_persistentcoursegrade gpcg ON sce.course_id = gpcg.course_id AND sce.user_id = gpcg.user_id
        WHERE sce.course_id = %s AND sce.is_active = 1
        ORDER BY u.username
    """, (course_id,))
    return {"learners": rows}

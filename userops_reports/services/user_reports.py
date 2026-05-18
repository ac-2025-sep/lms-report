from userops_reports.db import fetch_all_dict, fetch_one_dict
from userops_reports.services.common import as_float, as_int, iso


def search_users(query):
    search_pattern = f"%{query}%"
    rows = fetch_all_dict("""
        SELECT
            u.id as user_id,
            u.username,
            u.email,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.dealer_name')) as dealer_name,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.dealer_id')) as dealer_id,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.cluster')) as cluster,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.asm')) as asm,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.rsm')) as rsm,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.champion_name')) as champion_name,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.champion_mobile')) as champion_mobile,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.role')) as role,
            COUNT(DISTINCT sce.course_id) as courses_assigned,
            COUNT(DISTINCT CASE WHEN gc.id IS NOT NULL THEN sce.course_id END) as courses_completed,
            ROUND(AVG(COALESCE(gpcg.percent_grade, 0)) * 100, 1) as avg_progress
        FROM auth_user u
        JOIN auth_userprofile up ON u.id = up.user_id
        LEFT JOIN student_courseenrollment sce ON u.id = sce.user_id AND sce.is_active = 1
        LEFT JOIN certificates_generatedcertificate gc ON u.id = gc.user_id
            AND sce.course_id = gc.course_id AND gc.status = 'downloadable'
        LEFT JOIN grades_persistentcoursegrade gpcg ON u.id = gpcg.user_id
            AND sce.course_id = gpcg.course_id
        WHERE up.meta IS NOT NULL AND up.meta != '' AND up.meta != 'null' AND JSON_VALID(up.meta) = 1
          AND (
            u.username LIKE %s
            OR JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.dealer_name')) LIKE %s
            OR JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.dealer_id')) LIKE %s
          )
        GROUP BY u.id, u.username, u.email, up.meta
        ORDER BY
            CASE
                WHEN u.username LIKE %s THEN 1
                WHEN JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.dealer_name')) LIKE %s THEN 2
                ELSE 3
            END,
            u.username
        LIMIT 10
    """, (search_pattern, search_pattern, search_pattern, search_pattern, search_pattern))
    users = []
    for row in rows:
        users.append({
            "user_id": row["user_id"],
            "username": row["username"],
            "email": row["email"],
            "dealer_name": row.get("dealer_name") or row["username"],
            "dealer_id": row.get("dealer_id") or "N/A",
            "cluster": row.get("cluster") or "N/A",
            "asm": row.get("asm") or "N/A",
            "rsm": row.get("rsm") or "N/A",
            "champion_name": row.get("champion_name") or "N/A",
            "champion_mobile": row.get("champion_mobile") or "N/A",
            "role": row.get("role") or "N/A",
            "courses_assigned": as_int(row.get("courses_assigned")),
            "courses_completed": as_int(row.get("courses_completed")),
            "avg_progress": as_float(row.get("avg_progress")),
        })
    return {"users": users}


def get_user_details_by_username(username):
    user = fetch_one_dict("SELECT id FROM auth_user WHERE username = %s", (username,))
    if not user:
        return None
    return get_user_details_by_id(user["id"])


def get_user_details_by_id(user_id):
    row = fetch_one_dict("""
        SELECT
            u.id as user_id,
            u.username,
            u.email,
            u.date_joined,
            u.is_active,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.dealer_name')) as dealer_name,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.dealer_id')) as dealer_id,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.cluster')) as cluster,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.asm')) as asm,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.rsm')) as rsm,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.champion_name')) as champion_name,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.champion_mobile')) as champion_mobile,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.city')) as city,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.state')) as state,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.dealer_category')) as dealer_category,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.role')) as role,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.department')) as department,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.brand')) as brand,
            COUNT(DISTINCT sce.course_id) as total_courses_assigned,
            COUNT(DISTINCT CASE WHEN COALESCE(gpcg.percent_grade, 0) >= 1.0 THEN sce.course_id END) as courses_completed,
            COUNT(DISTINCT CASE WHEN COALESCE(gpcg.percent_grade, 0) > 0
                AND COALESCE(gpcg.percent_grade, 0) < 1.0 THEN sce.course_id END) as courses_in_progress,
            ROUND(AVG(COALESCE(gpcg.percent_grade, 0)) * 100, 1) as overall_progress
        FROM auth_user u
        JOIN auth_userprofile up ON u.id = up.user_id
        LEFT JOIN student_courseenrollment sce ON u.id = sce.user_id AND sce.is_active = 1
        LEFT JOIN grades_persistentcoursegrade gpcg ON u.id = gpcg.user_id
            AND sce.course_id = gpcg.course_id
        WHERE u.id = %s
        GROUP BY u.id, u.username, u.email, u.date_joined, u.is_active, up.meta
    """, (user_id,))
    if not row:
        return None

    course_rows = fetch_all_dict("""
        SELECT
            co.id as course_id,
            co.display_name as course_name,
            sce.created as enrollment_date,
            sce.mode as enrollment_mode,
            gc.id as certificate_id,
            gc.status as certificate_status,
            gc.created_date as completion_date,
            ROUND(gpcg.percent_grade * 100, 1) as grade,
            gpcg.letter_grade,
            COUNT(DISTINCT sm.id) as modules_completed,
            CASE
                WHEN gpcg.passed_timestamp IS NOT NULL OR COALESCE(gpcg.percent_grade, 0) >= 1.0 THEN 'completed'
                WHEN COUNT(sm.id) > 0 OR COALESCE(gpcg.percent_grade, 0) > 0 THEN 'in_progress'
                ELSE 'not_started'
            END as status
        FROM student_courseenrollment sce
        JOIN course_overviews_courseoverview co ON sce.course_id = co.id
        LEFT JOIN certificates_generatedcertificate gc ON sce.user_id = gc.user_id
            AND sce.course_id = gc.course_id AND gc.status = 'downloadable'
        LEFT JOIN courseware_studentmodule sm ON sce.user_id = sm.student_id
            AND sce.course_id = sm.course_id
        LEFT JOIN grades_persistentcoursegrade gpcg ON sce.user_id = gpcg.user_id
            AND sce.course_id = gpcg.course_id
        WHERE sce.user_id = %s AND sce.is_active = 1
        GROUP BY co.id, co.display_name, sce.created, sce.mode, gc.id, gc.status,
            gc.created_date, gpcg.percent_grade, gpcg.letter_grade, gpcg.passed_timestamp
        ORDER BY sce.created DESC
    """, (user_id,))
    courses = []
    for course in course_rows:
        courses.append({
            "course_id": course["course_id"],
            "course_name": course["course_name"],
            "enrollment_date": iso(course.get("enrollment_date")),
            "enrollment_mode": course.get("enrollment_mode"),
            "status": course.get("status") or "not_started",
            "grade": as_float(course.get("grade")),
            "letter_grade": course.get("letter_grade") or "N/A",
            "modules_completed": as_int(course.get("modules_completed")),
            "certificate_issued": course.get("certificate_id") is not None,
            "certificate_status": course.get("certificate_status"),
            "completion_date": iso(course.get("completion_date")),
        })

    return {
        "user_id": row["user_id"],
        "username": row["username"],
        "email": row["email"],
        "date_joined": iso(row.get("date_joined")),
        "is_active": bool(row.get("is_active")),
        "dealer_name": row.get("dealer_name") or row["username"],
        "dealer_id": row.get("dealer_id") or "N/A",
        "cluster": row.get("cluster") or "N/A",
        "asm": row.get("asm") or "N/A",
        "rsm": row.get("rsm") or "N/A",
        "champion_name": row.get("champion_name") or "N/A",
        "champion_mobile": row.get("champion_mobile") or "N/A",
        "city": row.get("city") or "N/A",
        "state": row.get("state") or "N/A",
        "dealer_category": row.get("dealer_category") or "N/A",
        "role": row.get("role") or "N/A",
        "department": row.get("department") or "N/A",
        "brand": row.get("brand") or "N/A",
        "total_courses_assigned": as_int(row.get("total_courses_assigned")),
        "courses_completed": as_int(row.get("courses_completed")),
        "courses_in_progress": as_int(row.get("courses_in_progress")),
        "overall_progress": as_float(row.get("overall_progress")),
        "courses": courses,
    }

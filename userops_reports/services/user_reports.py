from userops_reports.db import execute_query


def search_users(query):
    search_pattern = f"%{query}%"
    rows = execute_query("""
        SELECT u.id as user_id, u.username, u.email,
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
            ROUND(AVG(gpcg.percent_grade) * 100, 1) as avg_progress
        FROM auth_user u
        JOIN auth_userprofile up ON u.id = up.user_id
        LEFT JOIN student_courseenrollment sce ON u.id = sce.user_id AND sce.is_active = 1
        LEFT JOIN certificates_generatedcertificate gc ON u.id = gc.user_id AND sce.course_id = gc.course_id AND gc.status = 'downloadable'
        LEFT JOIN grades_persistentcoursegrade gpcg ON u.id = gpcg.user_id AND sce.course_id = gpcg.course_id
        WHERE up.meta IS NOT NULL AND up.meta != '' AND up.meta != 'null' AND JSON_VALID(up.meta) = 1
          AND (u.username LIKE %s OR JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.dealer_name')) LIKE %s OR JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.dealer_id')) LIKE %s)
        GROUP BY u.id, u.username, u.email, up.meta
        ORDER BY u.username
        LIMIT 10
    """, (search_pattern, search_pattern, search_pattern))
    return {"users": rows}


def get_user_details_by_username(username):
    rows = execute_query("""
        SELECT u.id as user_id, u.username, u.email, u.date_joined, u.is_active,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.dealer_name')) as dealer_name,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.dealer_id')) as dealer_id,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.cluster')) as cluster,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.asm')) as asm,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.rsm')) as rsm,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.champion_name')) as champion_name,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.champion_mobile')) as champion_mobile,
            COUNT(DISTINCT sce.course_id) as total_courses_assigned,
            COUNT(DISTINCT CASE WHEN gc.id IS NOT NULL THEN sce.course_id END) as courses_completed,
            ROUND(AVG(gpcg.percent_grade) * 100, 1) as overall_progress
        FROM auth_user u
        JOIN auth_userprofile up ON u.id = up.user_id
        LEFT JOIN student_courseenrollment sce ON u.id = sce.user_id AND sce.is_active = 1
        LEFT JOIN certificates_generatedcertificate gc ON u.id = gc.user_id AND sce.course_id = gc.course_id AND gc.status = 'downloadable'
        LEFT JOIN grades_persistentcoursegrade gpcg ON u.id = gpcg.user_id AND sce.course_id = gpcg.course_id
        WHERE u.username = %s
        GROUP BY u.id, u.username, u.email, u.date_joined, u.is_active, up.meta
    """, (username,))
    if not rows:
        return None
    row = rows[0]
    row["date_joined"] = row["date_joined"].isoformat() if row.get("date_joined") else None
    return row


def get_user_details_by_id(user_id):
    rows = execute_query("""
        SELECT u.id as user_id, u.username, u.email, u.date_joined, u.is_active,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.dealer_name')) as dealer_name,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.dealer_id')) as dealer_id,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.cluster')) as cluster,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.asm')) as asm,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.rsm')) as rsm,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.champion_name')) as champion_name,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.champion_mobile')) as champion_mobile,
            COUNT(DISTINCT sce.course_id) as total_courses_assigned,
            COUNT(DISTINCT CASE WHEN gc.id IS NOT NULL THEN sce.course_id END) as courses_completed,
            ROUND(AVG(gpcg.percent_grade) * 100, 1) as overall_progress
        FROM auth_user u
        JOIN auth_userprofile up ON u.id = up.user_id
        LEFT JOIN student_courseenrollment sce ON u.id = sce.user_id AND sce.is_active = 1
        LEFT JOIN certificates_generatedcertificate gc ON u.id = gc.user_id AND sce.course_id = gc.course_id AND gc.status = 'downloadable'
        LEFT JOIN grades_persistentcoursegrade gpcg ON u.id = gpcg.user_id AND sce.course_id = gpcg.course_id
        WHERE u.id = %s
        GROUP BY u.id, u.username, u.email, u.date_joined, u.is_active, up.meta
    """, (user_id,))
    if not rows:
        return None
    row = rows[0]
    row["date_joined"] = row["date_joined"].isoformat() if row.get("date_joined") else None
    return row

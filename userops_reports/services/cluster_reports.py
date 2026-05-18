from userops_reports.db import fetch_all_dict
from userops_reports.services.common import as_float, as_int, date_filter_clause, iso


def get_clusters():
    rows = fetch_all_dict("""
        SELECT DISTINCT JSON_UNQUOTE(JSON_EXTRACT(meta, '$.org.cluster')) as cluster
        FROM auth_userprofile
        WHERE meta IS NOT NULL AND meta != '' AND meta != 'null' AND JSON_VALID(meta) = 1
          AND JSON_UNQUOTE(JSON_EXTRACT(meta, '$.org.cluster')) IS NOT NULL
        ORDER BY cluster
    """)
    return {"clusters": [r["cluster"] for r in rows if r.get("cluster") and r.get("cluster") != "null"]}


def get_cluster_performance(date_range="all", start_date=None, end_date=None):
    date_clause, params = date_filter_clause("ce.created", date_range, start_date, end_date)
    query = f"""
        SELECT
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.cluster')) as cluster,
            COUNT(DISTINCT u.id) as total_users,
            COUNT(DISTINCT ce.course_id) as assigned_courses,
            COUNT(DISTINCT CASE WHEN COALESCE(gpcg.percent_grade, 0) >= 1.0 THEN ce.course_id END) as completed_courses,
            COUNT(DISTINCT CASE WHEN COALESCE(gpcg.percent_grade, 0) > 0
                AND COALESCE(gpcg.percent_grade, 0) < 1.0 THEN ce.course_id END) as in_progress,
            COUNT(DISTINCT CASE WHEN COALESCE(gpcg.percent_grade, 0) = 0 THEN ce.course_id END) as not_started,
            COALESCE(ROUND(AVG(COALESCE(gpcg.percent_grade, 0)) * 100, 1), 0) as avg_progress
        FROM auth_user u
        JOIN auth_userprofile up ON u.id = up.user_id
        LEFT JOIN student_courseenrollment ce ON u.id = ce.user_id AND ce.is_active = 1{date_clause}
        LEFT JOIN grades_persistentcoursegrade gpcg ON u.id = gpcg.user_id AND ce.course_id = gpcg.course_id
        WHERE up.meta IS NOT NULL AND up.meta != '' AND up.meta != 'null' AND JSON_VALID(up.meta) = 1
          AND JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.cluster')) IS NOT NULL
          AND JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.cluster')) != ''
        GROUP BY JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.cluster'))
        ORDER BY cluster
    """
    rows = fetch_all_dict(query, tuple(params))
    totals = {"assigned_courses": 0, "completed_courses": 0, "in_progress": 0, "not_started": 0, "total_users": 0, "avg_progress": 0}
    weighted = 0
    for row in rows:
        users = as_int(row.get("total_users"))
        row["total_users"] = users
        row["assigned_courses"] = as_int(row.get("assigned_courses"))
        row["completed_courses"] = as_int(row.get("completed_courses"))
        row["in_progress"] = as_int(row.get("in_progress"))
        row["not_started"] = as_int(row.get("not_started"))
        row["avg_progress"] = as_float(row.get("avg_progress"))
        totals["assigned_courses"] += row["assigned_courses"]
        totals["completed_courses"] += row["completed_courses"]
        totals["in_progress"] += row["in_progress"]
        totals["not_started"] += row["not_started"]
        totals["total_users"] += users
        weighted += row["avg_progress"] * users
    if totals["total_users"]:
        totals["avg_progress"] = round(weighted / totals["total_users"], 1)
    return {"clusters": rows, "totals": totals}


def get_asm_performance(cluster, date_range="all", start_date=None, end_date=None):
    date_clause, date_params = date_filter_clause("ce.created", date_range, start_date, end_date)
    query = f"""
        SELECT
            u.id as user_id, u.username, u.email, u.date_joined,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.dealer_name')) as dealer_name,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.dealer_id')) as dealer_id,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.asm')) as asm,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.rsm')) as rsm,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.champion_name')) as champion_name,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.champion_mobile')) as champion_mobile,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.city')) as city,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.state')) as state,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.dealer_category')) as dealer_category,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.brand')) as brand,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.role')) as role,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.department')) as department,
            COUNT(DISTINCT ce.course_id) as courses_assigned,
            COUNT(DISTINCT CASE WHEN COALESCE(gpcg.percent_grade, 0) >= 1.0 THEN ce.course_id END) as completed_courses,
            COUNT(DISTINCT CASE WHEN COALESCE(gpcg.percent_grade, 0) > 0
                AND COALESCE(gpcg.percent_grade, 0) < 1.0 THEN ce.course_id END) as in_progress,
            COUNT(DISTINCT CASE WHEN COALESCE(gpcg.percent_grade, 0) = 0 THEN ce.course_id END) as not_started,
            COALESCE(ROUND(AVG(COALESCE(gpcg.percent_grade, 0)) * 100, 1), 0) as avg_progress
        FROM auth_user u
        JOIN auth_userprofile up ON u.id = up.user_id
        LEFT JOIN student_courseenrollment ce ON u.id = ce.user_id AND ce.is_active = 1{date_clause}
        LEFT JOIN grades_persistentcoursegrade gpcg ON u.id = gpcg.user_id AND ce.course_id = gpcg.course_id
        WHERE up.meta IS NOT NULL AND up.meta != '' AND up.meta != 'null' AND JSON_VALID(up.meta) = 1
          AND JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.cluster')) = %s
        GROUP BY u.id, u.username, u.email, u.date_joined, up.meta
        ORDER BY dealer_name
    """
    rows = fetch_all_dict(query, tuple(date_params + [cluster]))
    dealers = []
    progress = 0
    for row in rows:
        dealer = {
            "user_id": row["user_id"],
            "username": row["username"],
            "email": row["email"],
            "date_joined": iso(row.get("date_joined")),
            "dealer_name": row.get("dealer_name") or "N/A",
            "dealer_id": row.get("dealer_id") or "N/A",
            "asm": row.get("asm") or "N/A",
            "rsm": row.get("rsm") or "N/A",
            "champion_name": row.get("champion_name") or row["username"],
            "champion_mobile": row.get("champion_mobile") or "N/A",
            "city": row.get("city") or "N/A",
            "state": row.get("state") or "N/A",
            "dealer_category": row.get("dealer_category") or "N/A",
            "brand": row.get("brand") or "N/A",
            "role": row.get("role") or "N/A",
            "department": row.get("department") or "N/A",
            "courses_assigned": as_int(row.get("courses_assigned")),
            "completed_courses": as_int(row.get("completed_courses")),
            "in_progress": as_int(row.get("in_progress")),
            "not_started": as_int(row.get("not_started")),
            "avg_progress": as_float(row.get("avg_progress")),
        }
        progress += dealer["avg_progress"]
        dealers.append(dealer)
    totals = {
        "dealers": len(dealers),
        "assigned_courses": sum(d["courses_assigned"] for d in dealers),
        "completed_courses": sum(d["completed_courses"] for d in dealers),
        "in_progress": sum(d["in_progress"] for d in dealers),
        "not_started": sum(d["not_started"] for d in dealers),
        "avg_progress": round(progress / len(dealers), 1) if dealers else 0,
    }
    return {"cluster": cluster, "totals": totals, "dealers": dealers}

from userops_reports.db import execute_query


def get_clusters():
    query = """
        SELECT DISTINCT JSON_UNQUOTE(JSON_EXTRACT(meta, '$.org.cluster')) as cluster
        FROM auth_userprofile
        WHERE meta IS NOT NULL AND meta != '' AND meta != 'null' AND JSON_VALID(meta) = 1
          AND JSON_UNQUOTE(JSON_EXTRACT(meta, '$.org.cluster')) IS NOT NULL
          AND JSON_UNQUOTE(JSON_EXTRACT(meta, '$.org.role')) = 'Champion'
        ORDER BY cluster
    """
    rows = execute_query(query)
    return {"clusters": [r["cluster"] for r in rows if r.get("cluster") and r.get("cluster") != "null"]}


def get_cluster_performance():
    query = """
        SELECT 
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.cluster')) as cluster,
            COUNT(DISTINCT u.id) as total_users,
            COUNT(DISTINCT ce.course_id) as assigned_courses,
            COUNT(DISTINCT CASE WHEN gc.id IS NOT NULL THEN ce.course_id END) as completed_courses,
            COUNT(DISTINCT CASE WHEN gc.id IS NULL AND sm.id IS NOT NULL THEN ce.course_id END) as in_progress,
            COUNT(DISTINCT CASE WHEN sm.id IS NULL THEN ce.course_id END) as not_started,
            COALESCE(ROUND(AVG(COALESCE((
                SELECT ROUND(AVG(sm2.grade) * 100, 1)
                FROM courseware_studentmodule sm2
                WHERE sm2.student_id = u.id AND sm2.course_id = ce.course_id AND sm2.grade IS NOT NULL
            ), 0)), 1), 0) as avg_progress
        FROM auth_user u
        JOIN auth_userprofile up ON u.id = up.user_id
        LEFT JOIN student_courseenrollment ce ON u.id = ce.user_id AND ce.is_active = 1
        LEFT JOIN certificates_generatedcertificate gc ON u.id = gc.user_id AND ce.course_id = gc.course_id AND gc.status = 'downloadable'
        LEFT JOIN courseware_studentmodule sm ON u.id = sm.student_id AND ce.course_id = sm.course_id
        WHERE up.meta IS NOT NULL AND up.meta != '' AND up.meta != 'null' AND JSON_VALID(up.meta) = 1
          AND JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.role')) = 'Champion'
          AND JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.cluster')) IS NOT NULL
          AND JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.cluster')) != ''
        GROUP BY JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.cluster'))
        ORDER BY cluster
    """
    rows = execute_query(query)
    totals = {"assigned_courses": 0, "completed_courses": 0, "in_progress": 0, "not_started": 0, "total_users": 0, "avg_progress": 0}
    weighted = 0
    for r in rows:
        users = int(r.get("total_users") or 0)
        totals["assigned_courses"] += int(r.get("assigned_courses") or 0)
        totals["completed_courses"] += int(r.get("completed_courses") or 0)
        totals["in_progress"] += int(r.get("in_progress") or 0)
        totals["not_started"] += int(r.get("not_started") or 0)
        totals["total_users"] += users
        weighted += float(r.get("avg_progress") or 0) * users
    if totals["total_users"]:
        totals["avg_progress"] = round(weighted / totals["total_users"], 1)
    return {"clusters": rows, "totals": totals}


def get_asm_performance(cluster):
    query = """
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
            COUNT(DISTINCT ce.course_id) as courses_assigned,
            COUNT(DISTINCT CASE WHEN gc.id IS NOT NULL THEN ce.course_id END) as completed_courses,
            COALESCE(ROUND(AVG(COALESCE((
                SELECT ROUND(AVG(sm.grade) * 100, 1)
                FROM courseware_studentmodule sm
                WHERE sm.student_id = u.id AND sm.course_id = ce.course_id AND sm.grade IS NOT NULL
            ), 0)), 1), 0) as avg_progress,
            COUNT(DISTINCT CASE WHEN gc.id IS NULL AND EXISTS (
                SELECT 1 FROM courseware_studentmodule sm
                WHERE sm.student_id = u.id AND sm.course_id = ce.course_id AND sm.grade IS NOT NULL LIMIT 1
            ) THEN ce.course_id END) as in_progress,
            COUNT(DISTINCT CASE WHEN NOT EXISTS (
                SELECT 1 FROM courseware_studentmodule sm
                WHERE sm.student_id = u.id AND sm.course_id = ce.course_id
            ) AND gc.id IS NULL THEN ce.course_id END) as not_started
        FROM auth_user u
        JOIN auth_userprofile up ON u.id = up.user_id
        LEFT JOIN student_courseenrollment ce ON u.id = ce.user_id AND ce.is_active = 1
        LEFT JOIN certificates_generatedcertificate gc ON u.id = gc.user_id AND ce.course_id = gc.course_id AND gc.status = 'downloadable'
        WHERE up.meta IS NOT NULL AND up.meta != '' AND up.meta != 'null' AND JSON_VALID(up.meta) = 1
          AND JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.role')) = 'Champion'
          AND JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.cluster')) = %s
        GROUP BY u.id, u.username, u.email, u.date_joined, up.meta
        ORDER BY dealer_name
    """
    rows = execute_query(query, (cluster,))
    dealers = []
    progress = 0
    for row in rows:
        dealer = {
            "user_id": row["user_id"], "username": row["username"], "email": row["email"],
            "date_joined": row["date_joined"].isoformat() if row.get("date_joined") else None,
            "dealer_name": row.get("dealer_name") or "N/A", "dealer_id": row.get("dealer_id") or "N/A",
            "asm": row.get("asm") or "N/A", "rsm": row.get("rsm") or "N/A",
            "champion_name": row.get("champion_name") or row["username"], "champion_mobile": row.get("champion_mobile") or "N/A",
            "city": row.get("city") or "N/A", "state": row.get("state") or "N/A", "dealer_category": row.get("dealer_category") or "N/A",
            "courses_assigned": int(row.get("courses_assigned") or 0), "completed_courses": int(row.get("completed_courses") or 0),
            "in_progress": int(row.get("in_progress") or 0), "not_started": int(row.get("not_started") or 0),
            "avg_progress": float(row.get("avg_progress") or 0),
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

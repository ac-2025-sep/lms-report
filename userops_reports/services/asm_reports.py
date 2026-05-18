from userops_reports.db import fetch_all_dict
from userops_reports.services.common import as_float, as_int, date_filter_clause, iso, meta_value, valid_meta


def get_asms():
    asm_expr = meta_value("auth_userprofile", "asm")
    rows = fetch_all_dict(f"""
        SELECT DISTINCT {asm_expr} as asm
        FROM auth_userprofile
        WHERE {valid_meta("auth_userprofile")}
          AND {asm_expr} IS NOT NULL
        ORDER BY asm
    """)
    return {"asms": [r["asm"] for r in rows if r.get("asm") and r.get("asm") != "null"]}


def get_rsms(date_range="all", start_date=None, end_date=None):
    date_clause, params = date_filter_clause("sce.created", date_range, start_date, end_date)
    rsm_expr = meta_value("up", "rsm")
    rows = fetch_all_dict(f"""
        SELECT
            rsm_name as name,
            SUM(total_dealers) as total_dealers,
            SUM(total_courses_assigned) as total_courses_assigned,
            SUM(courses_completed) as courses_completed,
            SUM(courses_in_progress) as courses_in_progress,
            ROUND(AVG(avg_progress), 1) as avg_progress
        FROM (
            SELECT
                COALESCE({rsm_expr}, 'Unknown') as rsm_name,
                COUNT(DISTINCT u.id) as total_dealers,
                COUNT(DISTINCT sce.course_id) as total_courses_assigned,
                COUNT(DISTINCT CASE WHEN COALESCE(gpcg.percent_grade, 0) >= 1.0 THEN sce.course_id END) as courses_completed,
                COUNT(DISTINCT CASE WHEN COALESCE(gpcg.percent_grade, 0) > 0
                    AND COALESCE(gpcg.percent_grade, 0) < 1.0 THEN sce.course_id END) as courses_in_progress,
                COALESCE(AVG(COALESCE(gpcg.percent_grade, 0)) * 100, 0) as avg_progress
            FROM auth_user u
            JOIN auth_userprofile up ON u.id = up.user_id
            LEFT JOIN student_courseenrollment sce ON u.id = sce.user_id AND sce.is_active = 1{date_clause}
            LEFT JOIN grades_persistentcoursegrade gpcg ON u.id = gpcg.user_id AND sce.course_id = gpcg.course_id
            WHERE {valid_meta("up")}
              AND {rsm_expr} IS NOT NULL
              AND {rsm_expr} != ''
              AND {rsm_expr} != 'null'
            GROUP BY u.id, COALESCE({rsm_expr}, 'Unknown')
        ) AS subquery
        WHERE rsm_name IS NOT NULL AND rsm_name != '' AND rsm_name != 'null'
        GROUP BY rsm_name
        ORDER BY rsm_name
    """, tuple(params))
    return {"rsms": rows}


def get_asm_dealers(asm, date_range="all", start_date=None, end_date=None):
    date_clause, date_params = date_filter_clause("ce.created", date_range, start_date, end_date)
    asm_expr = meta_value("up", "asm")
    rows = fetch_all_dict(f"""
        SELECT
            u.id as user_id, u.username, u.email, u.date_joined,
            {meta_value("up", "dealer_name")} as dealer_name,
            {meta_value("up", "dealer_id")} as dealer_id,
            {meta_value("up", "asm")} as asm,
            {meta_value("up", "rsm")} as rsm,
            {meta_value("up", "cluster")} as cluster,
            {meta_value("up", "champion_name")} as champion_name,
            {meta_value("up", "champion_mobile")} as champion_mobile,
            {meta_value("up", "city")} as city,
            {meta_value("up", "state")} as state,
            {meta_value("up", "dealer_category")} as dealer_category,
            {meta_value("up", "brand")} as brand,
            {meta_value("up", "role")} as role,
            {meta_value("up", "department")} as department,
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
        WHERE {valid_meta("up")}
          AND {asm_expr} = %s
        GROUP BY u.id, u.username, u.email, u.date_joined, up.meta
        ORDER BY dealer_name
    """, tuple(date_params + [asm]))
    dealers = []
    cluster_map = {}
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
            "cluster": row.get("cluster") or "Unassigned",
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
        dealers.append(dealer)
        cluster = dealer["cluster"]
        cluster_map.setdefault(cluster, {"name": cluster, "dealers": 0, "assigned_courses": 0, "completed_courses": 0, "in_progress": 0, "not_started": 0, "total_progress": 0})
        cluster_map[cluster]["dealers"] += 1
        cluster_map[cluster]["assigned_courses"] += dealer["courses_assigned"]
        cluster_map[cluster]["completed_courses"] += dealer["completed_courses"]
        cluster_map[cluster]["in_progress"] += dealer["in_progress"]
        cluster_map[cluster]["not_started"] += dealer["not_started"]
        cluster_map[cluster]["total_progress"] += dealer["avg_progress"]
    clusters = [
        {
            "name": c["name"],
            "dealers": c["dealers"],
            "assigned_courses": c["assigned_courses"],
            "completed_courses": c["completed_courses"],
            "in_progress": c["in_progress"],
            "not_started": c["not_started"],
            "avg_progress": round(c["total_progress"] / c["dealers"], 1) if c["dealers"] else 0,
        }
        for c in cluster_map.values()
    ]
    totals = {
        "dealers": len(dealers),
        "assigned_courses": sum(d["courses_assigned"] for d in dealers),
        "completed_courses": sum(d["completed_courses"] for d in dealers),
        "in_progress": sum(d["in_progress"] for d in dealers),
        "not_started": sum(d["not_started"] for d in dealers),
        "avg_progress": round(sum(d["avg_progress"] for d in dealers) / len(dealers), 1) if dealers else 0,
    }
    return {"asm": asm, "totals": totals, "dealers": dealers, "clusters": sorted(clusters, key=lambda item: item["name"])}


def get_asm_overview(date_range="all", start_date=None, end_date=None):
    overview = []
    for asm in get_asms().get("asms", []):
        dealers_data = get_asm_dealers(asm, date_range, start_date, end_date)
        totals = dealers_data["totals"]
        overview.append({
            "name": asm,
            "dealers": totals["dealers"],
            "assigned_courses": totals["assigned_courses"],
            "completed_courses": totals["completed_courses"],
            "in_progress": totals["in_progress"],
            "not_started": totals["not_started"],
            "avg_progress": totals["avg_progress"],
        })
    return overview

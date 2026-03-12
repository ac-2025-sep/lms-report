from userops_reports.db import fetch_all_dict


def get_asms():
    rows = fetch_all_dict("""
        SELECT DISTINCT JSON_UNQUOTE(JSON_EXTRACT(meta, '$.org.asm')) as asm
        FROM auth_userprofile
        WHERE meta IS NOT NULL AND meta != '' AND meta != 'null' AND JSON_VALID(meta) = 1
          AND JSON_UNQUOTE(JSON_EXTRACT(meta, '$.org.asm')) IS NOT NULL
          AND JSON_UNQUOTE(JSON_EXTRACT(meta, '$.org.role')) = 'Champion'
        ORDER BY asm
    """)
    return {"asms": [r["asm"] for r in rows if r.get("asm") and r.get("asm") != "null"]}


def get_rsms():
    rows = fetch_all_dict("""
        SELECT DISTINCT JSON_UNQUOTE(JSON_EXTRACT(meta, '$.org.rsm')) as rsm
        FROM auth_userprofile
        WHERE meta IS NOT NULL AND meta != '' AND meta != 'null' AND JSON_VALID(meta) = 1
          AND JSON_UNQUOTE(JSON_EXTRACT(meta, '$.org.rsm')) IS NOT NULL
          AND JSON_UNQUOTE(JSON_EXTRACT(meta, '$.org.role')) = 'Champion'
        ORDER BY rsm
    """)
    return {"rsms": [r["rsm"] for r in rows if r.get("rsm") and r.get("rsm") != "null"]}


def get_asm_dealers(asm):
    query = """
        SELECT u.id as user_id, u.username, u.email, u.date_joined,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.dealer_name')) as dealer_name,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.dealer_id')) as dealer_id,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.asm')) as asm,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.rsm')) as rsm,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.cluster')) as cluster,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.champion_name')) as champion_name,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.champion_mobile')) as champion_mobile,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.city')) as city,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.state')) as state,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.dealer_category')) as dealer_category,
            COUNT(DISTINCT ce.course_id) as courses_assigned,
            COUNT(DISTINCT CASE WHEN gc.id IS NOT NULL THEN ce.course_id END) as completed_courses,
            COALESCE(ROUND(AVG(COALESCE((
                SELECT ROUND(AVG(sm.grade) * 100, 1) FROM courseware_studentmodule sm
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
          AND JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.asm')) = %s
        GROUP BY u.id, u.username, u.email, u.date_joined, up.meta
        ORDER BY dealer_name
    """
    rows = fetch_all_dict(query, (asm,))
    dealers = []
    cluster_map = {}
    for row in rows:
        dealer = {
            "user_id": row["user_id"], "username": row["username"], "email": row["email"],
            "date_joined": row["date_joined"].isoformat() if row.get("date_joined") else None,
            "dealer_name": row.get("dealer_name") or "N/A", "dealer_id": row.get("dealer_id") or "N/A",
            "asm": row.get("asm") or "N/A", "rsm": row.get("rsm") or "N/A", "cluster": row.get("cluster") or "Unassigned",
            "champion_name": row.get("champion_name") or row["username"], "champion_mobile": row.get("champion_mobile") or "N/A",
            "city": row.get("city") or "N/A", "state": row.get("state") or "N/A", "dealer_category": row.get("dealer_category") or "N/A",
            "courses_assigned": int(row.get("courses_assigned") or 0), "completed_courses": int(row.get("completed_courses") or 0),
            "in_progress": int(row.get("in_progress") or 0), "not_started": int(row.get("not_started") or 0),
            "avg_progress": float(row.get("avg_progress") or 0),
        }
        dealers.append(dealer)
        c = dealer["cluster"]
        cluster_map.setdefault(c, {"name": c, "dealers": 0, "assigned_courses": 0, "completed_courses": 0, "in_progress": 0, "not_started": 0, "total_progress": 0})
        cluster_map[c]["dealers"] += 1
        cluster_map[c]["assigned_courses"] += dealer["courses_assigned"]
        cluster_map[c]["completed_courses"] += dealer["completed_courses"]
        cluster_map[c]["in_progress"] += dealer["in_progress"]
        cluster_map[c]["not_started"] += dealer["not_started"]
        cluster_map[c]["total_progress"] += dealer["avg_progress"]
    clusters = []
    for c in cluster_map.values():
        clusters.append({
            "name": c["name"], "dealers": c["dealers"], "assigned_courses": c["assigned_courses"],
            "completed_courses": c["completed_courses"], "in_progress": c["in_progress"],
            "not_started": c["not_started"], "avg_progress": round(c["total_progress"] / c["dealers"], 1) if c["dealers"] else 0,
        })
    totals = {
        "dealers": len(dealers),
        "assigned_courses": sum(d["courses_assigned"] for d in dealers),
        "completed_courses": sum(d["completed_courses"] for d in dealers),
        "in_progress": sum(d["in_progress"] for d in dealers),
        "not_started": sum(d["not_started"] for d in dealers),
        "avg_progress": round(sum(d["avg_progress"] for d in dealers) / len(dealers), 1) if dealers else 0,
    }
    return {"asm": asm, "totals": totals, "dealers": dealers, "clusters": sorted(clusters, key=lambda x: x["name"])}


def get_asm_overview():
    asms = get_asms().get("asms", [])
    overview = []
    for asm in asms:
        d = get_asm_dealers(asm)
        overview.append({"name": asm, **{k: d["totals"][k] for k in ["dealers", "assigned_courses", "completed_courses", "in_progress", "not_started", "avg_progress"]}})
    return overview

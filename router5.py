# lms_reports_router.py
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv
import logging
import json

load_dotenv()
logger = logging.getLogger(__name__)

# Database configuration


DB_CONFIG = {
    'host': os.getenv('HOST', 'edx.mysleepwell.com'),
    'database': os.getenv('MYSQL_DATABASE', 'openedx'),
    'user': os.getenv('MYSQL_USER', 'openedx'),
    'password': os.getenv('MYSQL_PASSWORD', '9gEi7luQ'),
    'port': os.getenv('MYSQL_PORT', 3306),
    'charset': 'utf8mb4'
}


def get_db_connection():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        logger.error(f"Error connecting to MySQL: {e}")
        return None

def execute_query(query: str, params: tuple = ()) -> Optional[List[Dict]]:
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        if not connection:
            return None
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, params)
        result = cursor.fetchall()
        return result
    except Error as e:
        logger.error(f"Query execution error: {e}")
        logger.error(f"Query: {query}")
        return None
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

# Create LMS Reports router
lms_reports_router5=lms_reports_router = APIRouter(prefix="/lms-reports", tags=["LMS Cluster/ASM Reports"])


# ================ CLUSTER ENDPOINTS ================

@lms_reports_router.get("/clusters")
async def get_all_clusters():
    """Get all unique clusters from user profiles"""
    query = """
        SELECT DISTINCT 
            JSON_UNQUOTE(JSON_EXTRACT(meta, '$.org.cluster')) as cluster
        FROM auth_userprofile
        WHERE meta IS NOT NULL 
            AND meta != '' 
            AND meta != 'null' 
            AND JSON_VALID(meta) = 1
            AND JSON_UNQUOTE(JSON_EXTRACT(meta, '$.org.cluster')) IS NOT NULL
            AND JSON_UNQUOTE(JSON_EXTRACT(meta, '$.org.role')) = 'Champion'
        ORDER BY cluster
    """
    
    result = execute_query(query)
    clusters = []
    for row in result or []:
        cluster = row.get('cluster')
        if cluster and cluster != 'null' and cluster != '':
            clusters.append(cluster)
    
    return {"clusters": clusters}

@lms_reports_router.get("/cluster-performance")
async def get_cluster_performance():
    """Get cluster-wise performance with accurate metrics"""
    
    query = """
        SELECT 
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.cluster')) as cluster,
            COUNT(DISTINCT u.id) as total_users,
            COUNT(DISTINCT ce.course_id) as assigned_courses,
            COUNT(DISTINCT CASE 
                WHEN gc.id IS NOT NULL THEN ce.course_id
            END) as completed_courses,
            COUNT(DISTINCT CASE 
                WHEN gc.id IS NULL AND sm.id IS NOT NULL THEN ce.course_id
            END) as in_progress,
            COUNT(DISTINCT CASE 
                WHEN sm.id IS NULL THEN ce.course_id
            END) as not_started,
            COALESCE(
                ROUND(
                    AVG(
                        COALESCE(
                            (SELECT 
                                ROUND(AVG(sm2.grade) * 100, 1)
                            FROM courseware_studentmodule sm2
                            WHERE sm2.student_id = u.id 
                            AND sm2.course_id = ce.course_id
                            AND sm2.grade IS NOT NULL), 0
                        )
                    ), 1
                ), 0
            ) as avg_progress
        FROM auth_user u
        JOIN auth_userprofile up ON u.id = up.user_id
        LEFT JOIN student_courseenrollment ce 
            ON u.id = ce.user_id AND ce.is_active = 1
        LEFT JOIN certificates_generatedcertificate gc 
            ON u.id = gc.user_id AND ce.course_id = gc.course_id
            AND gc.status = 'downloadable'
        LEFT JOIN courseware_studentmodule sm
            ON u.id = sm.student_id AND ce.course_id = sm.course_id
        WHERE 
            up.meta IS NOT NULL 
            AND up.meta != '' 
            AND up.meta != 'null' 
            AND JSON_VALID(up.meta) = 1
            AND JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.role')) = 'Champion'
            AND JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.cluster')) IS NOT NULL
            AND JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.cluster')) != ''
        GROUP BY JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.cluster'))
        ORDER BY cluster
    """
    
    result = execute_query(query)
    
    if not result:
        return {
            "clusters": [],
            "totals": {
                "assigned_courses": 0,
                "completed_courses": 0,
                "in_progress": 0,
                "not_started": 0,
                "total_users": 0,
                "avg_progress": 0
            }
        }
    
    totals = {
        "assigned_courses": 0,
        "completed_courses": 0,
        "in_progress": 0,
        "not_started": 0,
        "total_users": 0,
        "avg_progress": 0
    }
    
    total_progress_weighted = 0
    
    for row in result:
        assigned = int(row.get("assigned_courses") or 0)
        completed = int(row.get("completed_courses") or 0)
        in_progress = int(row.get("in_progress") or 0)
        not_started = int(row.get("not_started") or 0)
        users = int(row.get("total_users") or 0)
        
        totals["assigned_courses"] += assigned
        totals["completed_courses"] += completed
        totals["in_progress"] += in_progress
        totals["not_started"] += not_started
        totals["total_users"] += users
        
        cluster_progress = float(row.get("avg_progress") or 0)
        total_progress_weighted += cluster_progress * users
    
    if totals["total_users"] > 0:
        totals["avg_progress"] = round(total_progress_weighted / totals["total_users"], 1)
    
    return {
        "clusters": result,
        "totals": totals
    }


@lms_reports_router.get("/asm-performance/{cluster}")
async def get_asm_performance(cluster: str):
    """Get detailed dealer information for a specific cluster - FIXED field names"""
    
    query = """
        SELECT 
            u.id as user_id,
            u.username,
            u.email,
            u.date_joined,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.dealer_name')) as dealer_name,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.dealer_id')) as dealer_id,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.asm')) as asm,        -- asm field
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.rsm')) as rsm,        -- rsm field
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.champion_name')) as champion_name,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.champion_mobile')) as champion_mobile,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.city')) as city,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.state')) as state,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.dealer_category')) as dealer_category,
            COUNT(DISTINCT ce.course_id) as courses_assigned,
            COUNT(DISTINCT CASE 
                WHEN gc.id IS NOT NULL THEN ce.course_id
            END) as completed_courses,
            COALESCE(
                ROUND(
                    AVG(
                        COALESCE(
                            (SELECT 
                                ROUND(AVG(sm.grade) * 100, 1)
                            FROM courseware_studentmodule sm
                            WHERE sm.student_id = u.id 
                            AND sm.course_id = ce.course_id
                            AND sm.grade IS NOT NULL), 0
                        )
                    ), 1
                ), 0
            ) as avg_progress,
            COUNT(DISTINCT CASE 
                WHEN gc.id IS NULL 
                AND EXISTS (
                    SELECT 1 FROM courseware_studentmodule sm 
                    WHERE sm.student_id = u.id 
                    AND sm.course_id = ce.course_id
                    AND sm.grade IS NOT NULL
                    LIMIT 1
                ) THEN ce.course_id
            END) as in_progress,
            COUNT(DISTINCT CASE 
                WHEN NOT EXISTS (
                    SELECT 1 FROM courseware_studentmodule sm 
                    WHERE sm.student_id = u.id 
                    AND sm.course_id = ce.course_id
                ) AND gc.id IS NULL THEN ce.course_id
            END) as not_started
        FROM auth_user u
        JOIN auth_userprofile up ON u.id = up.user_id
        LEFT JOIN student_courseenrollment ce 
            ON u.id = ce.user_id AND ce.is_active = 1
        LEFT JOIN certificates_generatedcertificate gc 
            ON u.id = gc.user_id AND ce.course_id = gc.course_id
            AND gc.status = 'downloadable'
        WHERE 
            up.meta IS NOT NULL 
            AND up.meta != '' 
            AND up.meta != 'null' 
            AND JSON_VALID(up.meta) = 1
            AND JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.role')) = 'Champion'
            AND JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.cluster')) = %s
        GROUP BY u.id, u.username, u.email, u.date_joined, up.meta
        ORDER BY dealer_name
    """
    
    result = execute_query(query, (cluster,))
    
    if not result:
        return {
            "cluster": cluster,
            "totals": {
                "dealers": 0,
                "assigned_courses": 0,
                "completed_courses": 0,
                "in_progress": 0,
                "not_started": 0,
                "avg_progress": 0
            },
            "dealers": []
        }
    
    dealers = []
    totals = {
        "dealers": len(result),
        "assigned_courses": 0,
        "completed_courses": 0,
        "in_progress": 0,
        "not_started": 0,
        "avg_progress": 0
    }
    
    progress_sum = 0
    
    for row in result:
        dealer = {
            "user_id": row['user_id'],
            "username": row['username'],
            "email": row['email'],
            "date_joined": row['date_joined'].isoformat() if row['date_joined'] else None,
            "dealer_name": row['dealer_name'] or 'N/A',
            "dealer_id": row['dealer_id'] or 'N/A',
            "asm": row['asm'] or 'N/A',              # asm field
            "rsm": row['rsm'] or 'N/A',              # rsm field
            "champion_name": row['champion_name'] or row['username'],
            "champion_mobile": row['champion_mobile'] or 'N/A',
            "city": row['city'] or 'N/A',
            "state": row['state'] or 'N/A',
            "dealer_category": row['dealer_category'] or 'N/A',
            "courses_assigned": int(row['courses_assigned'] or 0),
            "completed_courses": int(row['completed_courses'] or 0),
            "in_progress": int(row['in_progress'] or 0),
            "not_started": int(row['not_started'] or 0),
            "avg_progress": float(row['avg_progress'] or 0)
        }
        
        dealers.append(dealer)
        
        totals['assigned_courses'] += dealer['courses_assigned']
        totals['completed_courses'] += dealer['completed_courses']
        totals['in_progress'] += dealer['in_progress']
        totals['not_started'] += dealer['not_started']
        progress_sum += dealer['avg_progress']
    
    if totals['dealers'] > 0:
        totals['avg_progress'] = round(progress_sum / totals['dealers'], 1)
    
    return {
        "cluster": cluster,
        "totals": totals,
        "dealers": dealers
    }


# ================ ASM ENDPOINTS ================

@lms_reports_router.get("/asms")
async def get_all_asms():
    """Get all unique ASMs from user profiles (from asm field)"""
    
    query = """
        SELECT DISTINCT 
            JSON_UNQUOTE(JSON_EXTRACT(meta, '$.org.asm')) as asm
        FROM auth_userprofile
        WHERE meta IS NOT NULL 
            AND meta != '' 
            AND meta != 'null' 
            AND JSON_VALID(meta) = 1
            AND JSON_UNQUOTE(JSON_EXTRACT(meta, '$.org.asm')) IS NOT NULL
            AND JSON_UNQUOTE(JSON_EXTRACT(meta, '$.org.role')) = 'Champion'
        ORDER BY asm
    """
    
    result = execute_query(query)
    asms = []
    for row in result or []:
        asm = row.get('asm')
        if asm and asm != 'null' and asm != '':
            asms.append(asm)
    
    return {"asms": asms}

@lms_reports_router.get("/rsms")
async def get_all_rsms():
    """Get all unique RSMs from user profiles (from rsm field)"""
    
    query = """
        SELECT DISTINCT 
            JSON_UNQUOTE(JSON_EXTRACT(meta, '$.org.rsm')) as rsm
        FROM auth_userprofile
        WHERE meta IS NOT NULL 
            AND meta != '' 
            AND meta != 'null' 
            AND JSON_VALID(meta) = 1
            AND JSON_UNQUOTE(JSON_EXTRACT(meta, '$.org.rsm')) IS NOT NULL
            AND JSON_UNQUOTE(JSON_EXTRACT(meta, '$.org.role')) = 'Champion'
        ORDER BY rsm
    """
    
    result = execute_query(query)
    rsms = []
    for row in result or []:
        rsm = row.get('rsm')
        if rsm and rsm != 'null' and rsm != '':
            rsms.append(rsm)
    
    return {"rsms": rsms}

@lms_reports_router.get("/asm-dealers/{asm}")
async def get_asm_dealers(asm: str):
    """Get all dealers under a specific ASM - UPDATED with asm/rsm naming"""
    
    query = """
        SELECT 
            u.id as user_id,
            u.username,
            u.email,
            u.date_joined,
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
            COUNT(DISTINCT CASE 
                WHEN gc.id IS NOT NULL THEN ce.course_id
            END) as completed_courses,
            COALESCE(
                ROUND(
                    AVG(
                        COALESCE(
                            (SELECT 
                                ROUND(AVG(sm.grade) * 100, 1)
                            FROM courseware_studentmodule sm
                            WHERE sm.student_id = u.id 
                            AND sm.course_id = ce.course_id
                            AND sm.grade IS NOT NULL), 0
                        )
                    ), 1
                ), 0
            ) as avg_progress,
            COUNT(DISTINCT CASE 
                WHEN gc.id IS NULL 
                AND EXISTS (
                    SELECT 1 FROM courseware_studentmodule sm 
                    WHERE sm.student_id = u.id 
                    AND sm.course_id = ce.course_id
                    AND sm.grade IS NOT NULL
                    LIMIT 1
                ) THEN ce.course_id
            END) as in_progress,
            COUNT(DISTINCT CASE 
                WHEN NOT EXISTS (
                    SELECT 1 FROM courseware_studentmodule sm 
                    WHERE sm.student_id = u.id 
                    AND sm.course_id = ce.course_id
                ) AND gc.id IS NULL THEN ce.course_id
            END) as not_started
        FROM auth_user u
        JOIN auth_userprofile up ON u.id = up.user_id
        LEFT JOIN student_courseenrollment ce 
            ON u.id = ce.user_id AND ce.is_active = 1
        LEFT JOIN certificates_generatedcertificate gc 
            ON u.id = gc.user_id AND ce.course_id = gc.course_id
            AND gc.status = 'downloadable'
        WHERE 
            up.meta IS NOT NULL 
            AND up.meta != '' 
            AND up.meta != 'null' 
            AND JSON_VALID(up.meta) = 1
            AND JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.role')) = 'Champion'
            AND JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.asm')) = %s
        GROUP BY u.id, u.username, u.email, u.date_joined, up.meta
        ORDER BY dealer_name
    """
    
    result = execute_query(query, (asm,))
    
    if not result:
        return {
            "asm": asm,
            "totals": {
                "dealers": 0,
                "assigned_courses": 0,
                "completed_courses": 0,
                "in_progress": 0,
                "not_started": 0,
                "avg_progress": 0
            },
            "dealers": [],
            "clusters": []
        }
    
    dealers = []
    cluster_map = {}
    
    for row in result:
        dealer = {
            "user_id": row['user_id'],
            "username": row['username'],
            "email": row['email'],
            "date_joined": row['date_joined'].isoformat() if row['date_joined'] else None,
            "dealer_name": row['dealer_name'] or 'N/A',
            "dealer_id": row['dealer_id'] or 'N/A',
            "asm": row['asm'] or 'N/A',
            "rsm": row['rsm'] or 'N/A',
            "cluster": row['cluster'] or 'Unassigned',
            "champion_name": row['champion_name'] or row['username'],
            "champion_mobile": row['champion_mobile'] or 'N/A',
            "city": row['city'] or 'N/A',
            "state": row['state'] or 'N/A',
            "dealer_category": row['dealer_category'] or 'N/A',
            "courses_assigned": int(row['courses_assigned'] or 0),
            "completed_courses": int(row['completed_courses'] or 0),
            "in_progress": int(row['in_progress'] or 0),
            "not_started": int(row['not_started'] or 0),
            "avg_progress": float(row['avg_progress'] or 0)
        }
        
        dealers.append(dealer)
        
        cluster_name = dealer['cluster']
        if cluster_name not in cluster_map:
            cluster_map[cluster_name] = {
                "name": cluster_name,
                "dealers": [],
                "assigned_courses": 0,
                "completed_courses": 0,
                "in_progress": 0,
                "not_started": 0,
                "total_progress": 0
            }
        
        cluster_map[cluster_name]["dealers"].append(dealer)
        cluster_map[cluster_name]["assigned_courses"] += dealer['courses_assigned']
        cluster_map[cluster_name]["completed_courses"] += dealer['completed_courses']
        cluster_map[cluster_name]["in_progress"] += dealer['in_progress']
        cluster_map[cluster_name]["not_started"] += dealer['not_started']
        cluster_map[cluster_name]["total_progress"] += dealer['avg_progress']
    
    clusters = []
    for cluster_name, cluster_data in cluster_map.items():
        dealer_count = len(cluster_data["dealers"])
        clusters.append({
            "name": cluster_name,
            "dealers": dealer_count,
            "assigned_courses": cluster_data["assigned_courses"],
            "completed_courses": cluster_data["completed_courses"],
            "in_progress": cluster_data["in_progress"],
            "not_started": cluster_data["not_started"],
            "avg_progress": round(cluster_data["total_progress"] / dealer_count, 1) if dealer_count > 0 else 0
        })
    
    totals = {
        "dealers": len(dealers),
        "assigned_courses": sum(d['courses_assigned'] for d in dealers),
        "completed_courses": sum(d['completed_courses'] for d in dealers),
        "in_progress": sum(d['in_progress'] for d in dealers),
        "not_started": sum(d['not_started'] for d in dealers),
        "avg_progress": round(sum(d['avg_progress'] for d in dealers) / len(dealers), 1) if dealers else 0
    }
    
    return {
        "asm": asm,
        "totals": totals,
        "dealers": dealers,
        "clusters": sorted(clusters, key=lambda x: x['name'])
    }

@lms_reports_router.get("/asm-overview")
async def get_asm_overview():
    """Get overview of all ASMs with aggregated metrics"""
    
    asms_data = await get_all_asms()
    asms = asms_data.get('asms', [])
    
    if not asms:
        return []
    
    overview = []
    for asm in asms:
        dealers_data = await get_asm_dealers(asm)
        overview.append({
            "name": asm,
            "dealers": dealers_data['totals']['dealers'],
            "assigned_courses": dealers_data['totals']['assigned_courses'],
            "completed_courses": dealers_data['totals']['completed_courses'],
            "in_progress": dealers_data['totals']['in_progress'],
            "not_started": dealers_data['totals']['not_started'],
            "avg_progress": dealers_data['totals']['avg_progress']
        })
    
    return overview

# ================ COURSE ENDPOINTS ================

@lms_reports_router.get("/courses")
async def get_all_courses_simple():
    """Get all courses for dropdown - simple list"""
    
    query = """
        SELECT 
            co.id as course_id,
            co.display_name as name
        FROM course_overviews_courseoverview co
        ORDER BY co.display_name
    """
    
    result = execute_query(query)
    
    if not result:
        return {"courses": []}
    
    courses = []
    for row in result:
        courses.append({
            "id": row['course_id'],
            "name": row['name'],
            "display_name": row['name']
        })
    
    return {"courses": courses}



@lms_reports_router.get("/courses/overview")
async def get_courses_overview():
    """Get overview of all courses with learner stats"""
    
    query = """
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
    -- Average of ALL learners, including zeros
    COALESCE(
        ROUND(
            AVG(COALESCE(gpcg.percent_grade, 0)) * 100, 
        2), 
    0) AS avg_grade,
    MAX(gpcg.modified) AS last_activity
FROM course_overviews_courseoverview co
LEFT JOIN student_courseenrollment sce 
    ON co.id = sce.course_id AND sce.is_active = 1
LEFT JOIN auth_userprofile up
    ON sce.user_id = up.user_id
LEFT JOIN certificates_generatedcertificate gc 
    ON sce.user_id = gc.user_id 
    AND sce.course_id = gc.course_id 
    AND gc.status = 'downloadable'
LEFT JOIN grades_persistentcoursegrade gpcg
    ON sce.course_id = gpcg.course_id
    AND sce.user_id = gpcg.user_id
WHERE up.meta IS NOT NULL 
    AND up.meta != '' 
    AND up.meta != 'null' 
    AND JSON_VALID(up.meta) = 1
GROUP BY co.id, co.display_name, co.start, co.end, co.org
ORDER BY co.display_name
    """
    
    result = execute_query(query)
    
    if not result:
        return {"courses": []}
    
    courses = []
    for row in result:
        courses.append({
            "course_id": row['course_id'],
            "course_name": row['course_name'],
            "total_enrollments": int(row['total_enrollments'] or 0),
            "certificates_issued": int(row['certificates_issued'] or 0),
            "active_learners": int(row['passed_count'] or 0),
            "avg_completion": float(row['avg_grade'] or 0),
            "last_activity": row['last_activity'].isoformat() if row['last_activity'] else None
        })
    
    return {"courses": courses}


@lms_reports_router.get("/courses/{course_id}")
async def get_course_details(course_id: str):
    """Get detailed statistics for a specific course - including zeros in average"""
    
    query = """
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
            -- Option A: Average of ALL learners, including zeros
            COALESCE(
                ROUND(
                    AVG(COALESCE(gpcg.percent_grade, 0)) * 100, 
                2), 
            0) AS avg_grade,
            MAX(gpcg.modified) AS last_activity
        FROM course_overviews_courseoverview co
        LEFT JOIN student_courseenrollment sce 
            ON co.id = sce.course_id AND sce.is_active = 1
        LEFT JOIN auth_userprofile up
            ON sce.user_id = up.user_id
        LEFT JOIN certificates_generatedcertificate gc 
            ON sce.user_id = gc.user_id 
            AND sce.course_id = gc.course_id 
            AND gc.status = 'downloadable'
        LEFT JOIN grades_persistentcoursegrade gpcg
            ON sce.course_id = gpcg.course_id
            AND sce.user_id = gpcg.user_id
        WHERE co.id = %s
          AND up.meta IS NOT NULL 
          AND up.meta != '' 
          AND up.meta != 'null' 
          AND JSON_VALID(up.meta) = 1
        GROUP BY co.id, co.display_name, co.start, co.end, co.org
    """
    
    result = execute_query(query, (course_id,))
    
    if not result or len(result) == 0:
        return {
            "course_id": course_id,
            "course_name": "Unknown Course",
            "start_date": None,
            "end_date": None,
            "org": None,
            "total_enrollments": 0,
            "certificates_issued": 0,
            "passed_count": 0,
            "in_progress_count": 0,
            "avg_grade": 0,
            "last_activity": None
        }
    
    row = result[0]
    
    return {
        "course_id": row['course_id'],
        "course_name": row['course_name'],
        "start_date": row['start'].isoformat() if row['start'] else None,
        "end_date": row['end'].isoformat() if row['end'] else None,
        "org": row['org'],
        "total_enrollments": int(row['total_enrollments'] or 0),
        "certificates_issued": int(row['certificates_issued'] or 0),
        "passed_count": int(row['passed_count'] or 0),
        "in_progress_count": int(row['in_progress_count'] or 0),
        "avg_grade": float(row['avg_grade'] or 0),
        "last_activity": row['last_activity'].isoformat() if row['last_activity'] else None
    }



@lms_reports_router.get("/courses/{course_id}/learners")
async def get_course_learners(course_id: str):
    """Get learners enrolled in a course with their progress - UPDATED with asm/rsm naming"""
    
    query = """
        SELECT
            sce.course_id,
            au.id AS user_id,
            au.username,
            au.email,
            up.meta,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.dealer_name')) as dealer_name,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.dealer_id')) as dealer_id,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.cluster')) as cluster,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.asm')) as asm,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.rsm')) as rsm,
            ROUND(gpcg.percent_grade * 100, 2) AS percent_grade,
            gpcg.letter_grade,
            CASE
                WHEN gpcg.passed_timestamp IS NOT NULL THEN 'Passed'
                ELSE 'Not Passed'
            END AS completion_status,
            gpcg.passed_timestamp,
            gpcg.modified AS grade_last_updated,
            sce.mode as enrollment_mode,
            sce.created as enrollment_date
        FROM student_courseenrollment AS sce
        JOIN auth_user AS au
            ON au.id = sce.user_id
        JOIN auth_userprofile AS up
            ON au.id = up.user_id
        LEFT JOIN grades_persistentcoursegrade AS gpcg
            ON gpcg.course_id = sce.course_id
           AND gpcg.user_id = sce.user_id
        WHERE sce.course_id = %s 
          AND sce.is_active = 1
          AND up.meta IS NOT NULL 
          AND up.meta != '' 
          AND up.meta != 'null' 
          AND JSON_VALID(up.meta) = 1
        ORDER BY 
            CASE 
                WHEN gpcg.passed_timestamp IS NOT NULL THEN 1
                WHEN gpcg.percent_grade > 0 THEN 2
                ELSE 3
            END,
            gpcg.percent_grade DESC
    """
    
    result = execute_query(query, (course_id,))
    
    learners = []
    for row in result or []:
        learners.append({
            "user_id": row['user_id'],
            "username": row['username'],
            "email": row['email'],
            "dealer_name": row['dealer_name'] or row['username'],
            "dealer_id": row['dealer_id'] or 'N/A',
            "cluster": row['cluster'] or 'Unassigned',
            "asm": row['asm'] or 'Unassigned',
            "rsm": row['rsm'] or 'Unassigned',
            "percent_grade": float(row['percent_grade'] or 0),
            "letter_grade": row['letter_grade'] or 'N/A',
            "completion_status": row['completion_status'],
            "passed_timestamp": row['passed_timestamp'].isoformat() if row['passed_timestamp'] else None,
            "grade_last_updated": row['grade_last_updated'].isoformat() if row['grade_last_updated'] else None,
            "enrollment_mode": row['enrollment_mode'],
            "enrollment_date": row['enrollment_date'].isoformat() if row['enrollment_date'] else None
        })
    
    return {"learners": learners}

@lms_reports_router.get("/courses/{course_id}/asms")
async def get_course_asms(course_id: str):
    """Get ASM-wise statistics for a specific course - UPDATED with asm field"""
    
    query = """
        SELECT 
            COALESCE(JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.asm')), 'Unassigned') as asm,
            COUNT(DISTINCT sce.user_id) as learners,
            COUNT(DISTINCT gc.id) as completed,
            COALESCE(ROUND(AVG(gpcg.percent_grade) * 100, 2), 0) as avg_completion
        FROM student_courseenrollment sce
        JOIN auth_user u ON sce.user_id = u.id
        JOIN auth_userprofile up ON u.id = up.user_id
        LEFT JOIN certificates_generatedcertificate gc 
            ON u.id = gc.user_id AND sce.course_id = gc.course_id
            AND gc.status = 'downloadable'
        LEFT JOIN grades_persistentcoursegrade gpcg
            ON sce.course_id = gpcg.course_id
            AND sce.user_id = gpcg.user_id
        WHERE sce.course_id = %s 
          AND sce.is_active = 1
          AND up.meta IS NOT NULL 
          AND up.meta != '' 
          AND up.meta != 'null' 
          AND JSON_VALID(up.meta) = 1
        GROUP BY JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.asm'))
        HAVING asm != 'Unassigned'
        ORDER BY avg_completion DESC
    """
    
    result = execute_query(query, (course_id,))
    
    if not result:
        return {"asms": []}
    
    asms = []
    for row in result:
        asms.append({
            "asm": row['asm'],
            "learners": int(row['learners'] or 0),
            "completed": int(row['completed'] or 0),
            "avg_completion": float(row['avg_completion'] or 0)
        })
    
    return {"asms": asms}

# ================ DASHBOARD METRICS ================

@lms_reports_router.get("/dashboard-metrics")
async def get_dashboard_metrics():
    """Get summary metrics for dashboard"""
    
    cluster_performance = await get_cluster_performance()
    asms_data = await get_all_asms()
    
    clusters = cluster_performance.get('clusters', [])
    
    total_dealers = 0
    total_progress_weighted = 0
    
    for cluster in clusters:
        dealers = int(cluster.get('total_users', 0))
        if dealers > 0:
            total_dealers += dealers
            print(
                "==>",cluster.get('avg_progress', 0)
            )
            cluster_progress = float(cluster.get('avg_progress', 0))
            total_progress_weighted += cluster_progress * dealers
    
    print(
        "tw",total_progress_weighted,
        'td',total_dealers
    )
    
    overall_progress = round(total_progress_weighted / total_dealers, 1) if total_dealers > 0 else 0
    
    return {
        "total_clusters": len(clusters),
        "total_asms": len(asms_data.get('asms', [])),
        "total_dealers": total_dealers,
        "total_assigned_courses": cluster_performance['totals']['assigned_courses'],
        "total_completed": cluster_performance['totals']['completed_courses'],
        "total_in_progress": cluster_performance['totals']['in_progress'],
        "total_not_started": cluster_performance['totals']['not_started'],
        "overall_progress": overall_progress,
        "clusters": clusters
    }

# ================ DEBUG ENDPOINTS ================

@lms_reports_router.get("/debug/check-data")
async def debug_check_data():
    """Debug endpoint to check what data exists in the database"""
    
    queries = {
        "users_with_champion_role": """
            SELECT COUNT(*) as count
            FROM auth_user u
            JOIN auth_userprofile up ON u.id = up.user_id
            WHERE 
                up.meta IS NOT NULL 
                AND up.meta != '' 
                AND up.meta != 'null' 
                AND JSON_VALID(up.meta) = 1
                AND JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.role')) = 'Champion'
        """,
        
        "clusters_found": """
            SELECT DISTINCT 
                JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.cluster')) as cluster,
                COUNT(*) as user_count
            FROM auth_user u
            JOIN auth_userprofile up ON u.id = up.user_id
            WHERE 
                up.meta IS NOT NULL 
                AND up.meta != '' 
                AND up.meta != 'null' 
                AND JSON_VALID(up.meta) = 1
                AND JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.role')) = 'Champion'
                AND JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.cluster')) IS NOT NULL
            GROUP BY JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.cluster'))
        """,
        
        "asms_found": """
            SELECT DISTINCT 
                JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.asm')) as asm,
                COUNT(*) as user_count
            FROM auth_user u
            JOIN auth_userprofile up ON u.id = up.user_id
            WHERE 
                up.meta IS NOT NULL 
                AND up.meta != '' 
                AND up.meta != 'null' 
                AND JSON_VALID(up.meta) = 1
                AND JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.role')) = 'Champion'
                AND JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.asm')) IS NOT NULL
            GROUP BY JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.asm'))
        """,
        
        "rsms_found": """
            SELECT DISTINCT 
                JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.rsm')) as rsm,
                COUNT(*) as user_count
            FROM auth_user u
            JOIN auth_userprofile up ON u.id = up.user_id
            WHERE 
                up.meta IS NOT NULL 
                AND up.meta != '' 
                AND up.meta != 'null' 
                AND JSON_VALID(up.meta) = 1
                AND JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.role')) = 'Champion'
                AND JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.rsm')) IS NOT NULL
            GROUP BY JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.rsm'))
        """
    }
    
    results = {}
    for key, query in queries.items():
        results[key] = execute_query(query)
    
    return results


@lms_reports_router.get("/debug/cluster/{cluster}")
async def debug_cluster_data(cluster: str):
    """Debug endpoint to check cluster data"""
    
    query = """
        SELECT 
            u.id,
            u.username,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.dealer_name')) as dealer_name,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.asm')) as asm,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.rsm')) as rsm,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.cluster')) as cluster
        FROM auth_user u
        JOIN auth_userprofile up ON u.id = up.user_id
        WHERE 
            up.meta IS NOT NULL 
            AND up.meta != '' 
            AND up.meta != 'null' 
            AND JSON_VALID(up.meta) = 1
            AND JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.role')) = 'Champion'
            AND JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.cluster')) = %s
    """
    
    result = execute_query(query, (cluster,))
    
    return {
        "cluster": cluster,
        "dealers": result,
        "count": len(result) if result else 0
    }

@lms_reports_router.get("/search/users")
async def search_users(query: str = Query(..., min_length=2)):
    """Search for users by username, dealer name, or dealer ID"""
    
    search_pattern = f"%{query}%"
    
    sql = """
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
            ROUND(AVG(gpcg.percent_grade) * 100, 1) as avg_progress
        FROM auth_user u
        JOIN auth_userprofile up ON u.id = up.user_id
        LEFT JOIN student_courseenrollment sce ON u.id = sce.user_id AND sce.is_active = 1
        LEFT JOIN certificates_generatedcertificate gc 
            ON u.id = gc.user_id AND sce.course_id = gc.course_id AND gc.status = 'downloadable'
        LEFT JOIN grades_persistentcoursegrade gpcg
            ON u.id = gpcg.user_id AND sce.course_id = gpcg.course_id
        WHERE 
            up.meta IS NOT NULL 
            AND up.meta != '' 
            AND up.meta != 'null' 
            AND JSON_VALID(up.meta) = 1
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
    """
    
    # Need 6 parameters: 3 for LIKE conditions, 3 for ORDER BY CASE
    params = (search_pattern, search_pattern, search_pattern, 
              search_pattern, search_pattern,)
    
    result = execute_query(sql, params)
    print(
        'result',result
    )
    
    users = []
    for row in result or []:
        users.append({
            "user_id": row['user_id'],
            "username": row['username'],
            "email": row['email'],
            "dealer_name": row['dealer_name'] or row['username'],
            "dealer_id": row['dealer_id'] or 'N/A',
            "cluster": row['cluster'] or 'N/A',
            "asm": row['asm'] or 'N/A',
            "rsm": row['rsm'] or 'N/A',
            "champion_name": row['champion_name'] or 'N/A',
            "champion_mobile": row['champion_mobile'] or 'N/A',
            "role": row['role'] or 'N/A',
            "courses_assigned": int(row['courses_assigned'] or 0),
            "courses_completed": int(row['courses_completed'] or 0),
            "avg_progress": float(row['avg_progress'] or 0)
        })
    
    return {"users": users}

@lms_reports_router.get("/users/{user_id}")
async def get_user_details(user_id: int):
    """Get detailed information for a specific user"""
    
    sql = """
        SELECT 
            u.id as user_id,
            u.username,
            u.email,
            u.date_joined,
            u.is_active,
            up.meta,
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
            COUNT(DISTINCT CASE WHEN gc.id IS NOT NULL THEN sce.course_id END) as courses_completed,
            COUNT(DISTINCT CASE WHEN gc.id IS NULL AND sm.id IS NOT NULL THEN sce.course_id END) as courses_in_progress,
            ROUND(AVG(gpcg.percent_grade) * 100, 1) as overall_progress
        FROM auth_user u
        JOIN auth_userprofile up ON u.id = up.user_id
        LEFT JOIN student_courseenrollment sce ON u.id = sce.user_id AND sce.is_active = 1
        LEFT JOIN certificates_generatedcertificate gc 
            ON u.id = gc.user_id AND sce.course_id = gc.course_id AND gc.status = 'downloadable'
        LEFT JOIN courseware_studentmodule sm 
            ON u.id = sm.student_id AND sce.course_id = sm.course_id
        LEFT JOIN grades_persistentcoursegrade gpcg
            ON u.id = gpcg.user_id AND sce.course_id = gpcg.course_id
        WHERE u.id = %s
        GROUP BY u.id, u.username, u.email, u.date_joined, u.is_active, up.meta
    """
    
    result = execute_query(sql, (user_id,))
    
    if not result or len(result) == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    row = result[0]
    
    # Get user's course details
    courses_sql = """
        SELECT 
            co.course_id,
            co.display_name as course_name,
            sce.created as enrollment_date,
            sce.mode as enrollment_mode,
            gc.id as certificate_id,
            gc.status as certificate_status,
            gc.created_date as completion_date,
            ROUND(gpcg.percent_grade * 100, 1) as grade,
            gpcg.letter_grade,
            CASE 
                WHEN gc.id IS NOT NULL THEN 'completed'
                WHEN sm.id IS NOT NULL THEN 'in_progress'
                ELSE 'not_started'
            END as status
        FROM student_courseenrollment sce
        JOIN course_overviews_courseoverview co ON sce.course_id = co.id
        LEFT JOIN certificates_generatedcertificate gc 
            ON sce.user_id = gc.user_id AND sce.course_id = gc.course_id AND gc.status = 'downloadable'
        LEFT JOIN courseware_studentmodule sm 
            ON sce.user_id = sm.student_id AND sce.course_id = sm.course_id
        LEFT JOIN grades_persistentcoursegrade gpcg
            ON sce.user_id = gpcg.user_id AND sce.course_id = gpcg.course_id
        WHERE sce.user_id = %s AND sce.is_active = 1
        GROUP BY co.course_id, co.display_name, sce.created, sce.mode, gc.id, gc.status, gc.created_date, gpcg.percent_grade, gpcg.letter_grade
        ORDER BY sce.created DESC
    """
    
    courses_result = execute_query(courses_sql, (user_id,))
    
    courses = []
    for course in courses_result or []:
        courses.append({
            "course_id": course['course_id'],
            "course_name": course['course_name'],
            "enrollment_date": course['enrollment_date'].isoformat() if course['enrollment_date'] else None,
            "enrollment_mode": course['enrollment_mode'],
            "status": course['status'],
            "grade": float(course['grade'] or 0),
            "letter_grade": course['letter_grade'] or 'N/A',
            "certificate_issued": course['certificate_id'] is not None,
            "certificate_status": course['certificate_status'],
            "completion_date": course['completion_date'].isoformat() if course['completion_date'] else None
        })
    
    return {
        "user_id": row['user_id'],
        "username": row['username'],
        "email": row['email'],
        "date_joined": row['date_joined'].isoformat() if row['date_joined'] else None,
        "is_active": bool(row['is_active']),
        "dealer_name": row['dealer_name'] or row['username'],
        "dealer_id": row['dealer_id'] or 'N/A',
        "cluster": row['cluster'] or 'N/A',
        "asm": row['asm'] or 'N/A',
        "rsm": row['rsm'] or 'N/A',
        "champion_name": row['champion_name'] or 'N/A',
        "champion_mobile": row['champion_mobile'] or 'N/A',
        "city": row['city'] or 'N/A',
        "state": row['state'] or 'N/A',
        "dealer_category": row['dealer_category'] or 'N/A',
        "role": row['role'] or 'N/A',
        "department": row['department'] or 'N/A',
        "brand": row['brand'] or 'N/A',
        "total_courses_assigned": int(row['total_courses_assigned'] or 0),
        "courses_completed": int(row['courses_completed'] or 0),
        "courses_in_progress": int(row['courses_in_progress'] or 0),
        "overall_progress": float(row['overall_progress'] or 0),
        "courses": courses
    }
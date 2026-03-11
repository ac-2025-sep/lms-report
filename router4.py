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
lms_reports_router4=lms_reports_router = APIRouter(prefix="/lms-reports", tags=["LMS Cluster/ASM Reports"])

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
            AND JSON_UNQUOTE(JSON_EXTRACT(meta, '$.org.cluster')) != ''
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

@lms_reports_router.get("/asms")
async def get_all_asms():
    """Get all unique ASMs (both ASM1 and ASM2) from user profiles"""
    query = """
        SELECT 
            JSON_UNQUOTE(JSON_EXTRACT(meta, '$.org.asm')) as asm1,
            JSON_UNQUOTE(JSON_EXTRACT(meta, '$.org.rsm')) as asm2
        FROM auth_userprofile
        WHERE meta IS NOT NULL 
            AND meta != '' 
            AND meta != 'null' 
            AND JSON_VALID(meta) = 1
            AND JSON_UNQUOTE(JSON_EXTRACT(meta, '$.org.role')) = 'Champion'
    """
    
    result = execute_query(query)
    asms = set()
    
    for row in result or []:
        asm1 = row.get('asm1')
        asm2 = row.get('asm2')
        
        if asm1 and asm1 != 'null' and asm1 != '':
            asms.add(asm1)
        if asm2 and asm2 != 'null' and asm2 != '':
            asms.add(asm2)
    
    return {"asms": sorted(list(asms))}



@lms_reports_router.get("/cluster-performance")
async def get_cluster_performance():
    """Get cluster-wise performance using completion_blockcompletion"""
    
    query = """
        SELECT 
    clusters.cluster,
    COUNT(DISTINCT clusters.user_id) as total_users,
    SUM(clusters.assigned_courses) as assigned_courses,
    SUM(clusters.completed_courses) as completed_courses,
    ROUND(AVG(clusters.user_avg_progress), 1) as avg_progress,
    SUM(clusters.in_progress_count) as in_progress,
    SUM(clusters.not_started_count) as not_started
FROM (
    SELECT 
        u.id as user_id,
        JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.cluster')) as cluster,
        COUNT(DISTINCT sce.course_id) as assigned_courses,
        COUNT(DISTINCT CASE WHEN cert.id IS NOT NULL THEN sce.course_id END) as completed_courses,
        -- Calculate user's average progress across all their courses
        COALESCE(
            ROUND(
                AVG(
                    COALESCE(
                        (SELECT 
                            ROUND(SUM(CASE WHEN cb.completion = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1)
                        FROM completion_blockcompletion cb
                        WHERE cb.user_id = sce.user_id 
                        AND cb.course_key = sce.course_id), 0
                    )
                ), 1
            ), 0
        ) as user_avg_progress,
        -- Count in-progress courses for this user
        COUNT(DISTINCT CASE 
            WHEN cert.id IS NULL 
            AND EXISTS (
                SELECT 1 FROM completion_blockcompletion cb 
                WHERE cb.user_id = sce.user_id 
                AND cb.course_key = sce.course_id
                AND cb.completion = 1
                LIMIT 1
            ) THEN sce.course_id
        END) as in_progress_count,
        -- Count not-started courses for this user
        COUNT(DISTINCT CASE 
            WHEN NOT EXISTS (
                SELECT 1 FROM completion_blockcompletion cb 
                WHERE cb.user_id = sce.user_id 
                AND cb.course_key = sce.course_id
                AND cb.completion = 1
            ) AND cert.id IS NULL THEN sce.course_id
        END) as not_started_count
    FROM auth_user u
    JOIN auth_userprofile up ON u.id = up.user_id
    LEFT JOIN student_courseenrollment sce ON u.id = sce.user_id AND sce.is_active = 1
    LEFT JOIN certificates_generatedcertificate cert 
        ON u.id = cert.user_id AND sce.course_id = cert.course_id
    WHERE 
        up.meta IS NOT NULL 
        AND up.meta != '' 
        AND up.meta != 'null' 
        AND JSON_VALID(up.meta) = 1
        AND JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.role')) = 'Champion'
        AND JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.cluster')) IS NOT NULL
        AND JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.cluster')) != ''
    GROUP BY u.id, up.meta
) clusters
WHERE clusters.cluster IS NOT NULL
GROUP BY clusters.cluster
ORDER BY clusters.cluster;
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
    
    # Calculate totals
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
    """Get detailed dealer information for a specific cluster using completion_blockcompletion"""
    
    query = """
        SELECT 
            u.id as user_id,
            u.username,
            u.email,
            u.date_joined,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.dealer_name')) as dealer_name,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.dealer_id')) as dealer_id,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.asm')) as asm_1,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.rsm')) as asm_2,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.champion_name')) as champion_name,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.champion_mobile')) as champion_mobile,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.city')) as city,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.state')) as state,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.dealer_category')) as dealer_category,
            COUNT(DISTINCT sce.course_id) as courses_assigned,
            COUNT(DISTINCT CASE 
                WHEN cert.id IS NOT NULL THEN sce.course_id
            END) as completed_courses,
            -- Calculate user's average progress across all their courses
            COALESCE(
                ROUND(
                    AVG(
                        COALESCE(
                            (SELECT 
                                ROUND(SUM(CASE WHEN cb.completion = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1)
                            FROM completion_blockcompletion cb
                            WHERE cb.user_id = sce.user_id 
                            AND cb.course_key = sce.course_id), 0
                        )
                    ), 1
                ), 0
            ) as avg_progress,
            -- Count in-progress courses for this user
            COUNT(DISTINCT CASE 
                WHEN cert.id IS NULL 
                AND EXISTS (
                    SELECT 1 FROM completion_blockcompletion cb 
                    WHERE cb.user_id = sce.user_id 
                    AND cb.course_key = sce.course_id
                    AND cb.completion = 1
                    LIMIT 1
                ) THEN sce.course_id
            END) as in_progress,
            -- Count not-started courses for this user
            COUNT(DISTINCT CASE 
                WHEN NOT EXISTS (
                    SELECT 1 FROM completion_blockcompletion cb 
                    WHERE cb.user_id = sce.user_id 
                    AND cb.course_key = sce.course_id
                    AND cb.completion = 1
                ) AND cert.id IS NULL THEN sce.course_id
            END) as not_started
        FROM auth_user u
        JOIN auth_userprofile up ON u.id = up.user_id
        LEFT JOIN student_courseenrollment sce ON u.id = sce.user_id AND sce.is_active = 1
        LEFT JOIN certificates_generatedcertificate cert 
            ON u.id = cert.user_id AND sce.course_id = cert.course_id
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
            "asm_1": row['asm_1'] or 'N/A',
            "asm_2": row['asm_2'] or 'N/A',
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


@lms_reports_router.get("/dealer-progress/{username}")
async def get_dealer_progress(username: str):
    """Get detailed course progress for a specific dealer using completion_blockcompletion"""
    
    query = """
        SELECT 
            co.display_name as course_name,
            co.course_id,
            sce.created as enrollment_date,
            sce.mode as enrollment_mode,
            cert.id as certificate_id,
            cert.status as certificate_status,
            cert.created_date as completion_date,
            -- Calculate progress from completion_blockcompletion
            COALESCE(
                ROUND(
                    (SELECT 
                        SUM(CASE WHEN cb.completion = 1 THEN 1 ELSE 0 END) * 100.0 / 
                        NULLIF(COUNT(*), 0)
                    FROM completion_blockcompletion cb
                    WHERE cb.user_id = sce.user_id 
                    AND cb.course_key = sce.course_id
                    ), 1
                ), 0
            ) as progress_percentage,
            -- Count completed blocks
            (SELECT COUNT(*) FROM completion_blockcompletion cb 
             WHERE cb.user_id = sce.user_id 
             AND cb.course_key = sce.course_id
             AND cb.completion = 1) as completed_blocks,
            -- Count total blocks
            (SELECT COUNT(*) FROM completion_blockcompletion cb 
             WHERE cb.user_id = sce.user_id 
             AND cb.course_key = sce.course_id) as total_blocks,
            -- Determine if course has any activity
            EXISTS (
                SELECT 1 FROM completion_blockcompletion cb 
                WHERE cb.user_id = sce.user_id 
                AND cb.course_key = sce.course_id
                LIMIT 1
            ) as has_activity
        FROM student_courseenrollment sce
        JOIN course_overviews_courseoverview co ON sce.course_id = co.course_id
        LEFT JOIN certificates_generatedcertificate cert 
            ON sce.user_id = cert.user_id AND sce.course_id = cert.course_id
        WHERE sce.user_id = (SELECT id FROM auth_user WHERE username = %s)
        AND sce.is_active = 1
        ORDER BY sce.created DESC
    """
    
    result = execute_query(query, (username,))
    
    courses = []
    for row in result or []:
        progress = float(row['progress_percentage'] or 0)
        
        # Determine status based on certificate and activity
        if row['certificate_id'] and row['certificate_status'] == 'downloadable':
            status = 'completed'
        elif row['has_activity'] and progress > 0:
            status = 'in_progress'
        else:
            status = 'not_started'
        
        courses.append({
            "course_name": row['course_name'],
            "course_id": row['course_id'],
            "enrollment_date": row['enrollment_date'].isoformat() if row['enrollment_date'] else None,
            "enrollment_mode": row['enrollment_mode'],
            "status": status,
            "progress_percentage": progress,
            "completed_blocks": row['completed_blocks'] or 0,
            "total_blocks": row['total_blocks'] or 0,
            "certificate_issued": row['certificate_id'] is not None,
            "certificate_status": row['certificate_status']
        })
    
    return courses




@lms_reports_router.get("/dashboard-metrics")
async def get_dashboard_metrics():
    """Get summary metrics for dashboard"""
    
    # Get cluster performance
    cluster_performance = await get_cluster_performance()
    
    # Get ASM list for count
    asms_data = await get_all_asms()
    
    clusters = cluster_performance.get('clusters', [])
    
    # Calculate weighted average progress
    total_dealers = 0
    total_progress_weighted = 0
    
    for cluster in clusters:
        dealers = int(cluster.get('total_users', 0))
        if dealers > 0:
            total_dealers += dealers
            cluster_progress = float(cluster.get('avg_progress', 0))
            total_progress_weighted += cluster_progress * dealers
    
    overall_progress = round(total_progress_weighted / total_dealers, 1) if total_dealers > 0 else 0
    
    return {
        "total_clusters": len(clusters),
        "total_asms": len(asms_data.get('asms', [])),
        "total_dealers": total_dealers,
        "total_assigned_courses": cluster_performance['totals']['assigned_courses'],
        "total_completed_courses": cluster_performance['totals']['completed_courses'],
        "total_in_progress": cluster_performance['totals']['in_progress'],
        "total_not_started": cluster_performance['totals']['not_started'],
        "overall_progress": overall_progress,
        "clusters": clusters
    }




@lms_reports_router.get("/export/{report_type}")
async def export_report(
    report_type: str,
    cluster: Optional[str] = None,
    asm: Optional[str] = None
):
    """Export report data in JSON format"""
    
    if report_type == "cluster-performance":
        report = await get_cluster_performance()
    elif report_type == "asm" and cluster:
        report = await get_asm_performance(cluster)
    elif report_type == "dashboard":
        report = await get_dashboard_metrics()
    else:
        raise HTTPException(status_code=400, detail="Invalid report type or missing parameters")
    
    # Add metadata
    report['exported_at'] = datetime.now().isoformat()
    report['report_type'] = report_type
    
    return report

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
        
        "enrollments_count": """
            SELECT COUNT(*) as count
            FROM student_courseenrollment
            WHERE is_active = 1
        """,
        
        "certificates_count": """
            SELECT COUNT(*) as count
            FROM certificates_generatedcertificate
            WHERE status = 'downloadable'
        """,
        
        "sample_user_meta": """
            SELECT 
                u.username,
                JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.role')) as role,
                JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.cluster')) as cluster,
                up.meta
            FROM auth_user u
            JOIN auth_userprofile up ON u.id = up.user_id
            WHERE 
                up.meta IS NOT NULL 
                AND up.meta != '' 
                AND up.meta != 'null' 
                AND JSON_VALID(up.meta) = 1
            LIMIT 1
        """
    }
    
    results = {}
    for key, query in queries.items():
        results[key] = execute_query(query)
    
    return results

@lms_reports_router.get("/debug/cluster/{cluster}")
async def debug_cluster(cluster: str):
    """Debug endpoint to check specific cluster data"""
    
    query = """
        SELECT 
            u.id,
            u.username,
            u.email,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.dealer_name')) as dealer_name,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.role')) as role,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.cluster')) as cluster,
            COUNT(DISTINCT sce.course_id) as enrollment_count,
            COUNT(DISTINCT cert.id) as certificate_count
        FROM auth_user u
        JOIN auth_userprofile up ON u.id = up.user_id
        LEFT JOIN student_courseenrollment sce ON u.id = sce.user_id AND sce.is_active = 1
        LEFT JOIN certificates_generatedcertificate cert 
            ON u.id = cert.user_id AND sce.course_id = cert.course_id
        WHERE 
            up.meta IS NOT NULL 
            AND up.meta != '' 
            AND up.meta != 'null' 
            AND JSON_VALID(up.meta) = 1
            AND JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.cluster')) = %s
        GROUP BY u.id, u.username, u.email, up.meta
    """
    
    result = execute_query(query, (cluster,))
    
    return {
        "cluster": cluster,
        "users": result,
        "count": len(result) if result else 0
    }

@lms_reports_router.get("/asm-dealers/{asm}")
async def get_asm_dealers(asm: str):
    """Get all dealers under a specific ASM (from both ASM1 and ASM2 fields)"""
    
    query = """
        SELECT 
            u.id as user_id,
            u.username,
            u.email,
            u.date_joined,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.dealer_name')) as dealer_name,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.dealer_id')) as dealer_id,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.asm')) as asm_1,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.rsm')) as asm_2,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.cluster')) as cluster,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.champion_name')) as champion_name,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.champion_mobile')) as champion_mobile,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.city')) as city,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.state')) as state,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.dealer_category')) as dealer_category,
            COUNT(DISTINCT sce.course_id) as courses_assigned,
            COUNT(DISTINCT CASE 
                WHEN cert.id IS NOT NULL THEN sce.course_id
            END) as completed_courses,
            -- Calculate user's average progress across all their courses
            COALESCE(
                ROUND(
                    AVG(
                        COALESCE(
                            (SELECT 
                                ROUND(SUM(CASE WHEN cb.completion = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1)
                            FROM completion_blockcompletion cb
                            WHERE cb.user_id = sce.user_id 
                            AND cb.course_key = sce.course_id), 0
                        )
                    ), 1
                ), 0
            ) as avg_progress,
            -- Count in-progress courses for this user
            COUNT(DISTINCT CASE 
                WHEN cert.id IS NULL 
                AND EXISTS (
                    SELECT 1 FROM completion_blockcompletion cb 
                    WHERE cb.user_id = sce.user_id 
                    AND cb.course_key = sce.course_id
                    AND cb.completion = 1
                    LIMIT 1
                ) THEN sce.course_id
            END) as in_progress,
            -- Count not-started courses for this user
            COUNT(DISTINCT CASE 
                WHEN NOT EXISTS (
                    SELECT 1 FROM completion_blockcompletion cb 
                    WHERE cb.user_id = sce.user_id 
                    AND cb.course_key = sce.course_id
                    AND cb.completion = 1
                ) AND cert.id IS NULL THEN sce.course_id
            END) as not_started
        FROM auth_user u
        JOIN auth_userprofile up ON u.id = up.user_id
        LEFT JOIN student_courseenrollment sce ON u.id = sce.user_id AND sce.is_active = 1
        LEFT JOIN certificates_generatedcertificate cert 
            ON u.id = cert.user_id AND sce.course_id = cert.course_id
        LEFT JOIN completion_blockcompletion cb ON u.id = cb.user_id AND sce.course_id = cb.course_key
        WHERE 
            up.meta IS NOT NULL 
            AND up.meta != '' 
            AND up.meta != 'null' 
            AND JSON_VALID(up.meta) = 1
            AND JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.role')) = 'Champion'
            AND (
                JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.asm')) = %s
                OR JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.rsm')) = %s
            )
        GROUP BY u.id, u.username, u.email, u.date_joined, up.meta
        ORDER BY dealer_name
    """
    
    result = execute_query(query, (asm, asm))
    
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
            "asm_1": row['asm_1'] or 'N/A',
            "asm_2": row['asm_2'] or 'N/A',
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
        
        # Group by cluster
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
    
    # Calculate cluster averages
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
    
    # Calculate totals
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
    
    # First get all unique ASMs
    asms_data = await get_all_asms()
    asms = asms_data.get('asms', [])
    
    result = []
    for asm in asms:
        # Get dealers under this ASM
        dealers_data = await get_asm_dealers(asm)
        
        result.append({
            "name": asm,
            "dealers": dealers_data['totals']['dealers'],
            "assigned_courses": dealers_data['totals']['assigned_courses'],
            "completed_courses": dealers_data['totals']['completed_courses'],
            "in_progress": dealers_data['totals']['in_progress'],
            "not_started": dealers_data['totals']['not_started'],
            "avg_progress": dealers_data['totals']['avg_progress'],
            "clusters": len(dealers_data['clusters'])
        })
    
    # Sort by name
    result.sort(key=lambda x: x['name'])
    
    return result


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
    """Get overview of all courses with learner stats and avg completion"""
    
    query = """
        SELECT 
            co.id AS course_id,
            co.display_name AS course_name,
            COUNT(DISTINCT ce.user_id) AS total_enrollments,
            COUNT(DISTINCT gc.id) AS certificates_issued,
            COUNT(DISTINCT sm.student_id) AS active_learners,
            COALESCE(ROUND(AVG(sm.grade) * 100, 2), 0) AS avg_completion,
            MAX(sm.modified) AS last_activity,
            MAX(co.modified) AS last_updated
        FROM course_overviews_courseoverview co
        LEFT JOIN student_courseenrollment ce 
            ON co.id = ce.course_id AND ce.is_active = 1
        LEFT JOIN certificates_generatedcertificate gc 
            ON ce.user_id = gc.user_id 
            AND ce.course_id = gc.course_id 
            AND gc.status = 'downloadable'
        LEFT JOIN courseware_studentmodule sm 
            ON ce.user_id = sm.student_id 
            AND ce.course_id = sm.course_id
        GROUP BY co.id, co.display_name
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
            "active_learners": int(row['active_learners'] or 0),
            "avg_completion": float(row['avg_completion'] or 0),
            "last_activity": row['last_activity'].isoformat() if row['last_activity'] else None,
            "last_updated": row['last_updated'].isoformat() if row['last_updated'] else None
        })
    
    return {"courses": courses}


@lms_reports_router.get("/courses/{course_id}")
async def get_course_details(course_id: str):
    """Get detailed statistics for a specific course"""
    
    query = """
        SELECT 
            co.id AS course_id,
            co.display_name AS course_name,
            co.start,
            co.end,
            co.org,
            COUNT(DISTINCT ce.user_id) AS total_enrollments,
            COUNT(DISTINCT gc.id) AS certificates_issued,
            COUNT(DISTINCT sm.student_id) AS active_learners,
            COALESCE(ROUND(AVG(sm.grade) * 100, 2), 0) AS avg_completion,
            MAX(sm.modified) AS last_activity
        FROM course_overviews_courseoverview co
        LEFT JOIN student_courseenrollment ce 
            ON co.id = ce.course_id AND ce.is_active = 1
        LEFT JOIN certificates_generatedcertificate gc 
            ON ce.user_id = gc.user_id 
            AND ce.course_id = gc.course_id 
            AND gc.status = 'downloadable'
        LEFT JOIN courseware_studentmodule sm 
            ON ce.user_id = sm.student_id 
            AND ce.course_id = sm.course_id
        WHERE co.id = %s
        GROUP BY co.id, co.display_name, co.start, co.end, co.org
    """
    
    result = execute_query(query, (course_id,))
    
    if not result or len(result) == 0:
        # Return default values instead of 404 to prevent frontend errors
        return {
            "course_id": course_id,
            "course_name": "Unknown Course",
            "start_date": None,
            "end_date": None,
            "org": None,
            "total_enrollments": 0,
            "certificates_issued": 0,
            "active_learners": 0,
            "avg_completion": 0,
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
        "active_learners": int(row['active_learners'] or 0),
        "avg_completion": float(row['avg_completion'] or 0),
        "last_activity": row['last_activity'].isoformat() if row['last_activity'] else None
    }


@lms_reports_router.get("/courses/{course_id}/modules")
async def get_course_modules(course_id: str):
    """Get module-wise completion statistics for a specific course"""
    
    query = """
        SELECT
            module_id,
            COUNT(DISTINCT student_id) AS learners_attempted,
            ROUND(AVG(grade) * 100, 2) AS avg_completion,
            MAX(grade) AS max_grade,
            MIN(grade) AS min_grade,
            COUNT(*) AS total_attempts,
            MAX(modified) AS last_activity
        FROM courseware_studentmodule
        WHERE course_id = %s
        GROUP BY module_id
        ORDER BY avg_completion DESC
    """
    
    result = execute_query(query, (course_id,))
    
    if not result:
        return {"modules": []}
    
    modules = []
    for row in result:
        # Extract readable module name and type
        module_parts = row['module_id'].split('@')
        module_type = module_parts[-2] if len(module_parts) > 2 else 'unknown'
        module_name = module_parts[-1] if module_parts else row['module_id']
        
        modules.append({
            "module_id": row['module_id'],
            "module_type": module_type,
            "module_name": module_name,
            "learners_attempted": int(row['learners_attempted'] or 0),
            "avg_completion": float(row['avg_completion'] or 0),
            "max_grade": float(row['max_grade'] or 0) * 100,
            "min_grade": float(row['min_grade'] or 0) * 100,
            "total_attempts": int(row['total_attempts'] or 0),
            "last_activity": row['last_activity'].isoformat() if row['last_activity'] else None
        })
    
    return {"modules": modules}


@lms_reports_router.get("/courses/{course_id}/learners")
async def get_course_learners(course_id: str):
    """Get learners enrolled in a course with their progress"""
    
    query = """
        SELECT 
            u.id as user_id,
            u.username,
            u.email,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.dealer_name')) as dealer_name,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.dealer_id')) as dealer_id,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.cluster')) as cluster,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.asm')) as asm,
            JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.rsm')) as rsm,
            ce.mode as enrollment_mode,
            ce.created as enrollment_date,
            gc.id as certificate_id,
            gc.status as certificate_status,
            -- Calculate progress based on completed blocks vs total blocks
            COALESCE(
                (
                    SELECT 
                        ROUND(
                            COUNT(CASE WHEN cb.completion = 1 THEN 1 END) * 100.0 / 
                            NULLIF(COUNT(*), 0), 1
                        )
                    FROM completion_blockcompletion cb
                    WHERE cb.user_id = u.id 
                    AND cb.course_key = ce.course_id
                ), 0
            ) as progress,
            -- Count completed modules
            (
                SELECT COUNT(*)
                FROM completion_blockcompletion cb
                WHERE cb.user_id = u.id 
                AND cb.course_key = ce.course_id
                AND cb.completion = 1
            ) as modules_completed,
            -- Count total modules in course for this user
            (
                SELECT COUNT(*)
                FROM completion_blockcompletion cb
                WHERE cb.user_id = u.id 
                AND cb.course_key = ce.course_id
            ) as total_modules,
            -- Last activity
            (
                SELECT MAX(modified)
                FROM completion_blockcompletion cb
                WHERE cb.user_id = u.id 
                AND cb.course_key = ce.course_id
            ) as last_activity,
            -- Status determination
            CASE 
                WHEN gc.id IS NOT NULL AND gc.status = 'downloadable' THEN 'completed'
                WHEN EXISTS (
                    SELECT 1 FROM completion_blockcompletion cb 
                    WHERE cb.user_id = u.id 
                    AND cb.course_key = ce.course_id
                    AND cb.completion = 1
                    LIMIT 1
                ) THEN 'in_progress'
                ELSE 'not_started'
            END as status
        FROM student_courseenrollment ce
        INNER JOIN auth_user u ON ce.user_id = u.id
        INNER JOIN auth_userprofile up ON u.id = up.user_id
        LEFT JOIN certificates_generatedcertificate gc 
            ON u.id = gc.user_id AND ce.course_id = gc.course_id
            AND gc.status = 'downloadable'
        WHERE ce.course_id = %s 
            AND ce.is_active = 1
            AND up.meta IS NOT NULL 
            AND up.meta != '' 
            AND up.meta != 'null' 
            AND JSON_VALID(up.meta) = 1
        ORDER BY 
            CASE 
                WHEN gc.id IS NOT NULL THEN 1
                WHEN EXISTS (
                    SELECT 1 FROM completion_blockcompletion cb 
                    WHERE cb.user_id = u.id 
                    AND cb.course_key = ce.course_id
                    AND cb.completion = 1
                ) THEN 2
                ELSE 3
            END,
            progress DESC
    """
    
    result = execute_query(query, (course_id,))
    
    learners = []
    for row in result or []:
        learners.append({
            "user_id": row['user_id'],
            "username": row['username'],
            "email": row['email'],
            "dealer_name": row['dealer_name'] or row['username'] or 'N/A',
            "dealer_id": row['dealer_id'] or 'N/A',
            "cluster": row['cluster'] or 'N/A',
            "asm": row['asm'] or 'N/A',
            "rsm": row['rsm'] or 'N/A',
            "enrollment_mode": row['enrollment_mode'],
            "enrollment_date": row['enrollment_date'].isoformat() if row['enrollment_date'] else None,
            "certificate_id": row['certificate_id'],
            "certificate_status": row['certificate_status'],
            "progress": float(row['progress'] or 0),
            "modules_completed": int(row['modules_completed'] or 0),
            "total_modules": int(row['total_modules'] or 0),
            "last_activity": row['last_activity'].isoformat() if row['last_activity'] else None,
            "status": row['status']
        })
    
    return {"learners": learners}

    


@lms_reports_router.get("/courses/{course_id}/clusters")
async def get_course_clusters(course_id: str):
    """Get cluster-wise performance statistics for a specific course"""
    
    query = """
        SELECT 
            COALESCE(JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.cluster')), 'Unassigned') as cluster,
            COUNT(DISTINCT ce.user_id) as total_learners,
            COUNT(DISTINCT gc.id) as completed,
            COUNT(DISTINCT CASE WHEN sm.id IS NOT NULL AND gc.id IS NULL THEN ce.user_id END) as in_progress,
            COUNT(DISTINCT CASE WHEN sm.id IS NULL THEN ce.user_id END) as not_started,
            COALESCE(ROUND(AVG(sm.grade) * 100, 2), 0) as avg_completion
        FROM student_courseenrollment ce
        JOIN auth_user u ON ce.user_id = u.id
        JOIN auth_userprofile up ON u.id = up.user_id
        LEFT JOIN certificates_generatedcertificate gc 
            ON u.id = gc.user_id AND ce.course_id = gc.course_id
            AND gc.status = 'downloadable'
        LEFT JOIN courseware_studentmodule sm 
            ON u.id = sm.student_id AND ce.course_id = sm.course_id
        WHERE ce.course_id = %s AND ce.is_active = 1
        GROUP BY JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.cluster'))
        ORDER BY avg_completion DESC
    """
    
    result = execute_query(query, (course_id,))
    
    if not result:
        return {"clusters": []}
    
    clusters = []
    for row in result:
        clusters.append({
            "cluster": row['cluster'],
            "total_learners": int(row['total_learners'] or 0),
            "completed": int(row['completed'] or 0),
            "in_progress": int(row['in_progress'] or 0),
            "not_started": int(row['not_started'] or 0),
            "avg_completion": float(row['avg_completion'] or 0)
        })
    
    return {"clusters": clusters}



@lms_reports_router.get("/courses/{course_id}/asms")
async def get_course_asms(course_id: str):
    """Get ASM-wise performance statistics for a specific course"""
    
    query = """
        SELECT 
            COALESCE(JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.asm')), 'Unassigned') as asm,
            COUNT(DISTINCT ce.user_id) as total_learners,
            COUNT(DISTINCT gc.id) as completed,
            COALESCE(ROUND(AVG(sm.grade) * 100, 2), 0) as avg_completion
        FROM student_courseenrollment ce
        JOIN auth_user u ON ce.user_id = u.id
        JOIN auth_userprofile up ON u.id = up.user_id
        LEFT JOIN certificates_generatedcertificate gc 
            ON u.id = gc.user_id AND ce.course_id = gc.course_id
            AND gc.status = 'downloadable'
        LEFT JOIN courseware_studentmodule sm 
            ON u.id = sm.student_id AND ce.course_id = sm.course_id
        WHERE ce.course_id = %s AND ce.is_active = 1
        GROUP BY JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.asm'))
        ORDER BY avg_completion DESC
    """
    
    result = execute_query(query, (course_id,))
    
    if not result:
        return {"asms": []}
    
    asms = []
    for row in result:
        asms.append({
            "asm": row['asm'],
            "total_learners": int(row['total_learners'] or 0),
            "completed": int(row['completed'] or 0),
            "avg_completion": float(row['avg_completion'] or 0)
        })
    
    return {"asms": asms}
    
@lms_reports_router.get("/courses/{course_id}/rsms")
async def get_course_rsms(course_id: str):
    """Get RSM-wise performance statistics for a specific course"""
    
    query = """
        SELECT 
            COALESCE(JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.rsm')), 'Unassigned') as rsm,
            COUNT(DISTINCT ce.user_id) as total_learners,
            COUNT(DISTINCT gc.id) as completed,
            COALESCE(ROUND(AVG(sm.grade) * 100, 2), 0) as avg_completion
        FROM student_courseenrollment ce
        JOIN auth_user u ON ce.user_id = u.id
        JOIN auth_userprofile up ON u.id = up.user_id
        LEFT JOIN certificates_generatedcertificate gc 
            ON u.id = gc.user_id AND ce.course_id = gc.course_id
            AND gc.status = 'downloadable'
        LEFT JOIN courseware_studentmodule sm 
            ON u.id = sm.student_id AND ce.course_id = sm.course_id
        WHERE ce.course_id = %s AND ce.is_active = 1
        GROUP BY JSON_UNQUOTE(JSON_EXTRACT(up.meta, '$.org.rsm'))
        ORDER BY avg_completion DESC
    """
    
    result = execute_query(query, (course_id,))
    
    if not result:
        return {"rsms": []}
    
    rsms = []
    for row in result:
        rsms.append({
            "rsm": row['rsm'],
            "total_learners": int(row['total_learners'] or 0),
            "completed": int(row['completed'] or 0),
            "avg_completion": float(row['avg_completion'] or 0)
        })
    
    return {"rsms": rsms}

@lms_reports_router.get("/courses/{course_id}/progress-distribution")
async def get_course_progress_distribution(course_id: str):
    """Get progress distribution (buckets) for a course"""
    
    query = """
        SELECT 
            CASE 
                WHEN sm.grade IS NULL THEN 'not_started'
                WHEN sm.grade >= 0.9 THEN '90-100%'
                WHEN sm.grade >= 0.8 THEN '80-89%'
                WHEN sm.grade >= 0.7 THEN '70-79%'
                WHEN sm.grade >= 0.6 THEN '60-69%'
                WHEN sm.grade >= 0.5 THEN '50-59%'
                WHEN sm.grade >= 0.25 THEN '25-49%'
                WHEN sm.grade > 0 THEN '1-24%'
                ELSE '0%'
            END as progress_bucket,
            COUNT(DISTINCT ce.user_id) as learner_count
        FROM student_courseenrollment ce
        LEFT JOIN courseware_studentmodule sm 
            ON ce.user_id = sm.student_id AND ce.course_id = sm.course_id
        WHERE ce.course_id = %s AND ce.is_active = 1
        GROUP BY progress_bucket
        ORDER BY 
            CASE progress_bucket
                WHEN 'not_started' THEN 1
                WHEN '0%' THEN 2
                WHEN '1-24%' THEN 3
                WHEN '25-49%' THEN 4
                WHEN '50-59%' THEN 5
                WHEN '60-69%' THEN 6
                WHEN '70-79%' THEN 7
                WHEN '80-89%' THEN 8
                WHEN '90-100%' THEN 9
                ELSE 10
            END
    """
    
    result = execute_query(query, (course_id,))
    
    if not result:
        return {"distribution": []}
    
    return {"distribution": result}
import logging
from contextlib import closing

from django.db import connection

logger = logging.getLogger(__name__)


class ReportQueryError(Exception):
    """Raised when report SQL execution fails."""


def fetch_all_dict(sql, params=None):
    query_params = params or ()
    try:
        with closing(connection.cursor()) as cursor:
            cursor.execute(sql, query_params)
            columns = [col[0] for col in (cursor.description or [])]
            if not columns:
                return []
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except Exception:
        logger.exception("Report query failed")
        raise ReportQueryError("Report query failed")


def fetch_one_dict(sql, params=None):
    rows = fetch_all_dict(sql, params=params)
    return rows[0] if rows else None


def execute_query(query, params=()):
    """Backward-compatible alias for previous service imports."""
    return fetch_all_dict(query, params=params)

import logging
from contextlib import closing

from django.db import connection

logger = logging.getLogger(__name__)


class ReportQueryError(Exception):
    """Raised when report SQL execution fails."""


def execute_query(query, params=()):
    try:
        with closing(connection.cursor()) as cursor:
            cursor.execute(query, params)
            columns = [col[0] for col in cursor.description] if cursor.description else []
            return [dict(zip(columns, row)) for row in cursor.fetchall()] if columns else []
    except Exception:
        logger.exception("Report query failed")
        raise ReportQueryError("Report query failed")

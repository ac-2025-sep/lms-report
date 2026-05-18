from datetime import date, datetime, timedelta


def get_date_range(date_range="all", start_date=None, end_date=None):
    today = date.today()

    if not date_range or date_range == "all":
        return None, None
    if date_range == "today":
        return today, today
    if date_range == "yesterday":
        yesterday = today - timedelta(days=1)
        return yesterday, yesterday
    if date_range == "this_week":
        return today - timedelta(days=today.weekday()), today
    if date_range == "last_week":
        start = today - timedelta(days=today.weekday() + 7)
        return start, start + timedelta(days=6)
    if date_range == "this_month":
        return date(today.year, today.month, 1), today
    if date_range == "last_month":
        if today.month == 1:
            return date(today.year - 1, 12, 1), date(today.year - 1, 12, 31)
        start = date(today.year, today.month - 1, 1)
        return start, date(today.year, today.month, 1) - timedelta(days=1)
    if date_range == "last_3_months":
        return today - timedelta(days=90), today
    if date_range == "last_6_months":
        return today - timedelta(days=180), today
    if date_range == "this_year":
        return date(today.year, 1, 1), today
    if date_range == "custom" and start_date and end_date:
        try:
            return (
                datetime.strptime(start_date, "%Y-%m-%d").date(),
                datetime.strptime(end_date, "%Y-%m-%d").date(),
            )
        except ValueError:
            return None, None
    return None, None


def date_filter_clause(column, date_range="all", start_date=None, end_date=None):
    start, end = get_date_range(date_range, start_date, end_date)
    if start and end:
        return f" AND {column} BETWEEN %s AND %s", [start, end]
    return "", []


def iso(value):
    return value.isoformat() if value else None


def as_int(value):
    return int(value or 0)


def as_float(value):
    return float(value or 0)

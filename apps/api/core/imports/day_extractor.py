"""Filter RawRows to only those belonging to the requested day/date."""

import re
from datetime import date, datetime
from typing import Optional

from .constants import WEEKDAY_NAMES
from .grid_parser import RawRow


class DayResolutionError(ValueError):
    pass


def resolve_target_date(
    target_day: Optional[str] = None,
    target_date: Optional[str] = None,
) -> tuple[Optional[date], Optional[str]]:
    """
    Resolve the operator's day/date input into (resolved_date, weekday_name).

    Rules:
    - target_date (YYYY-MM-DD) takes precedence; weekday_name is derived from it.
    - target_day (e.g. "Tuesday") is used when only a weekday name is given;
      resolved_date will be None in that case.
    - Both may be supplied; they must agree on the weekday.
    """
    resolved_date: Optional[date] = None
    weekday_name: Optional[str] = None

    if target_date:
        try:
            resolved_date = date.fromisoformat(target_date)
        except ValueError:
            raise DayResolutionError(
                f"Invalid target_date '{target_date}'. Use YYYY-MM-DD format."
            )
        weekday_name = resolved_date.strftime("%A").lower()

    if target_day:
        provided_wd = target_day.strip().lower()
        if provided_wd not in WEEKDAY_NAMES:
            raise DayResolutionError(
                f"Unknown weekday '{target_day}'. "
                "Use: Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday."
            )
        if weekday_name and weekday_name != provided_wd and not weekday_name.startswith(provided_wd[:3]):
            raise DayResolutionError(
                f"target_day '{target_day}' does not match the weekday of "
                f"target_date '{target_date}' ({weekday_name.capitalize()})."
            )
        weekday_name = provided_wd

    return resolved_date, weekday_name


_DATE_FORMATS = [
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%m/%d/%Y",
    "%d %b %Y",
    "%d %B %Y",
    "%d %b %y",
    "%d/%m/%y",
]


def parse_row_date(date_str: str) -> Optional[date]:
    """Try to parse a date string using common formats. Returns None on failure."""
    if not date_str:
        return None
    date_str = date_str.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None


def row_matches_target(
    row: RawRow,
    target_date: Optional[date],
    weekday_name: Optional[str],
) -> bool:
    """
    Return True if this row's day/date info matches the target.

    If the row has no day/date column information, it is included
    (the sheet may contain only one day's data).
    """
    # --- Check date column ---
    if row.date_str:
        parsed = parse_row_date(row.date_str)
        if parsed is not None:
            if target_date and parsed == target_date:
                return True
            if weekday_name and parsed.strftime("%A").lower() == weekday_name:
                return True
            # Has a parseable date but it doesn't match — exclude.
            if target_date or weekday_name:
                return False

    # --- Check day column ---
    if row.day:
        row_day = row.day.strip().lower()
        for wd_name, wd_num in WEEKDAY_NAMES.items():
            if wd_name in row_day or row_day in wd_name:
                if weekday_name and wd_name.startswith(weekday_name[:3]):
                    return True
                if target_date and wd_num == target_date.weekday():
                    return True
        return False

    # No day/date info — include by default
    return True


def filter_rows_by_day(
    rows: list[RawRow],
    target_date: Optional[date],
    weekday_name: Optional[str],
) -> list[RawRow]:
    """
    Return only rows that belong to the specified day/date.
    If neither is provided, all rows are returned unchanged.
    """
    if not target_date and not weekday_name:
        return rows
    return [r for r in rows if row_matches_target(r, target_date, weekday_name)]

"""Convert a RawRow into a normalised session dict ready for validation."""

import re
from datetime import date, datetime, time, timedelta
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings

from .constants import (
    DEFAULT_PUBLISH_MODE,
    DEFAULT_REQUIRES_MEET,
    DEFAULT_SCHEDULED_FOR_OFFSET_MINUTES,
)
from .day_extractor import parse_row_date
from .grid_parser import RawRow

_TIME_FORMATS = ["%H:%M", "%I:%M %p", "%I:%M%p", "%H.%M", "%H:%M:%S"]


def parse_time_str(time_str: str) -> Optional[time]:
    """Parse a time string in common formats. Returns None on failure."""
    if not time_str:
        return None
    time_str = time_str.strip()
    for fmt in _TIME_FORMATS:
        try:
            return datetime.strptime(time_str, fmt).time()
        except ValueError:
            continue
    return None


def build_title(row: RawRow) -> str:
    """Build a best-effort session title from available row fields."""
    if row.title:
        return row.title
    parts = [p for p in (row.subject, row.topic) if p]
    if parts:
        return " — ".join(parts)
    return ""


def build_topic_label(
    target_date: Optional[date],
    weekday_name: Optional[str],
) -> str:
    if target_date:
        return target_date.strftime("%A") + " Sessions"
    if weekday_name:
        return weekday_name.capitalize() + " Sessions"
    return ""


def compute_scheduled_for(
    session_date: date,
    start: time,
) -> Optional[datetime]:
    """Return a timezone-aware datetime = session start + configured offset."""
    try:
        tz = ZoneInfo(settings.TIME_ZONE)
    except (ZoneInfoNotFoundError, AttributeError):
        tz = ZoneInfo("UTC")
    try:
        naive_dt = datetime.combine(session_date, start)
        aware_dt = naive_dt.replace(tzinfo=tz)
        return aware_dt + timedelta(minutes=DEFAULT_SCHEDULED_FOR_OFFSET_MINUTES)
    except Exception:
        return None


def normalize_row(
    row: RawRow,
    target_date: Optional[date],
    weekday_name: Optional[str],
    course_map_id: Optional[int],
) -> dict:
    """
    Convert a RawRow into a flat dict representing a candidate SessionDraft.

    Keys match SessionDraft model fields plus 'row_index' and 'course_map_id'.
    """
    # Resolve date — prefer explicitly provided target_date, fall back to row's date column.
    resolved_date: Optional[date] = target_date
    if resolved_date is None and row.date_str:
        resolved_date = parse_row_date(row.date_str)

    start_t = parse_time_str(row.start_time_str)
    end_t = parse_time_str(row.end_time_str)
    title = build_title(row)
    topic_label = build_topic_label(target_date, weekday_name)

    scheduled_for = None
    if resolved_date and start_t:
        scheduled_for = compute_scheduled_for(resolved_date, start_t)

    # Faculty/room/extra notes appended to notes field.
    notes_parts = [p for p in (
        f"Faculty: {row.faculty}" if row.faculty else "",
        f"Room: {row.room}" if row.room else "",
        row.notes,
    ) if p]
    notes = " | ".join(notes_parts)

    return {
        "row_index": row.row_index,
        "course_map_id": course_map_id,
        "date": resolved_date.isoformat() if resolved_date else None,
        "start_time": start_t.strftime("%H:%M") if start_t else None,
        "end_time": end_t.strftime("%H:%M") if end_t else None,
        "title": title,
        "subject": row.subject,
        "topic": row.topic,
        "subgroup_label": row.group,
        "requires_meet": DEFAULT_REQUIRES_MEET,
        "publish_mode": DEFAULT_PUBLISH_MODE,
        "scheduled_for": scheduled_for.isoformat() if scheduled_for else None,
        "topic_label": topic_label,
        "notes": notes,
    }

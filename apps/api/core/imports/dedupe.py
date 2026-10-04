"""Stable dedupe hash for session drafts to prevent duplicate imports."""

import hashlib


def compute_dedupe_hash(
    course_id: int | None,
    date: str | None,
    start_time: str | None,
    title: str | None,
    subgroup_label: str = "",
    publish_mode: str = "scheduled",
) -> str:
    """
    Return a 64-character hex SHA-256 hash that uniquely identifies a session
    by its content-addressable properties.

    Any two session rows with the same course, date, start time, title,
    subgroup and publish mode will produce the same hash regardless of how many
    times the sheet is imported.
    """
    parts = [
        str(course_id or ""),
        str(date or ""),
        str(start_time or ""),
        (title or "").strip().lower(),
        (subgroup_label or "").strip().lower(),
        (publish_mode or "").lower(),
    ]
    key = "|".join(parts)
    return hashlib.sha256(key.encode()).hexdigest()

"""
Parse a raw Google Sheets grid (2-D list of strings) into structured RawRow objects.

Handles:
- Auto-detecting the header row and mapping columns to known fields
- Separate start/end time columns
- Combined time column ("09:40-10:30")
- Blank/inherited cells caused by visual merging
- Skipping spacer rows
"""

import re
from dataclasses import dataclass, field
from typing import Optional

from .constants import (
    COMBINED_TIME_KEYWORDS,
    DAY_KEYWORDS,
    DATE_KEYWORDS,
    END_TIME_KEYWORDS,
    FACULTY_KEYWORDS,
    GROUP_KEYWORDS,
    NOTES_KEYWORDS,
    ROOM_KEYWORDS,
    START_TIME_KEYWORDS,
    SUBJECT_KEYWORDS,
    TITLE_KEYWORDS,
    TOPIC_KEYWORDS,
)


@dataclass
class ColumnMap:
    day: Optional[int] = None
    date: Optional[int] = None
    start_time: Optional[int] = None
    end_time: Optional[int] = None
    combined_time: Optional[int] = None
    subject: Optional[int] = None
    title: Optional[int] = None
    topic: Optional[int] = None
    group: Optional[int] = None
    faculty: Optional[int] = None
    room: Optional[int] = None
    notes: Optional[int] = None

    def has_time_info(self) -> bool:
        return (
            self.combined_time is not None
            or self.start_time is not None
            or self.end_time is not None
        )

    def has_content_info(self) -> bool:
        return any(
            x is not None for x in (self.subject, self.title, self.topic)
        )


@dataclass
class RawRow:
    row_index: int  # 1-based, matches sheet row number
    values: list[str] = field(default_factory=list)
    day: str = ""
    date_str: str = ""
    start_time_str: str = ""
    end_time_str: str = ""
    subject: str = ""
    title: str = ""
    topic: str = ""
    group: str = ""
    faculty: str = ""
    room: str = ""
    notes: str = ""


def _normalise_key(cell: str) -> str:
    """Lowercase + collapse non-alphanumeric to underscore."""
    return re.sub(r"[^a-z0-9]", "_", cell.strip().lower())


def _matches(cell: str, keywords: set) -> bool:
    key = _normalise_key(cell)
    # Check exact membership first, then check if any keyword appears inside the normalised key.
    # We deliberately do NOT check the reverse (key inside keyword) to avoid "time" falsely
    # matching "start_time" or "end_time".
    return key in keywords or any(kw in key for kw in keywords)


def _get(row: list[str], idx: Optional[int], default: str = "") -> str:
    if idx is None or idx >= len(row):
        return default
    return str(row[idx]).strip()


def _pad(row: list[str], length: int) -> list[str]:
    if len(row) < length:
        return list(row) + [""] * (length - len(row))
    return list(row)


def parse_combined_time(time_str: str) -> tuple[Optional[str], Optional[str]]:
    """
    Parse "09:40-10:30" or "9:40 – 10:30" into (start, end) strings.
    Returns (None, None) if the pattern is not recognised.
    """
    m = re.search(r"(\d{1,2}:\d{2})\s*[-\u2013\u2014]\s*(\d{1,2}:\d{2})", time_str.strip())
    if m:
        return m.group(1), m.group(2)
    return None, None


def detect_header_row(grid: list[list[str]]) -> tuple[int, ColumnMap]:
    """
    Scan the first 25 rows to find the header row.

    A row qualifies as the header if it contains matches for at least 2 known
    field categories AND at least one time-related category.

    Returns (header_row_index, ColumnMap).  If no confident header is found the
    first non-empty row is returned with an empty ColumnMap.
    """
    best: tuple[int, ColumnMap, int] = (-1, ColumnMap(), 0)

    for row_idx, row in enumerate(grid[:25]):
        if not row or all(not str(c).strip() for c in row):
            continue

        col_map = ColumnMap()
        matched = 0

        for col_idx, raw_cell in enumerate(row):
            cell = str(raw_cell).strip()
            if not cell:
                continue

            if _matches(cell, DAY_KEYWORDS) and col_map.day is None:
                col_map.day = col_idx; matched += 1
            elif _matches(cell, DATE_KEYWORDS) and col_map.date is None:
                col_map.date = col_idx; matched += 1
            elif _matches(cell, START_TIME_KEYWORDS) and col_map.start_time is None:
                col_map.start_time = col_idx; matched += 1
            elif _matches(cell, END_TIME_KEYWORDS) and col_map.end_time is None:
                col_map.end_time = col_idx; matched += 1
            elif _matches(cell, COMBINED_TIME_KEYWORDS) and col_map.combined_time is None:
                col_map.combined_time = col_idx; matched += 1
            elif _matches(cell, SUBJECT_KEYWORDS) and col_map.subject is None:
                col_map.subject = col_idx; matched += 1
            elif _matches(cell, TITLE_KEYWORDS) and col_map.title is None:
                col_map.title = col_idx; matched += 1
            elif _matches(cell, TOPIC_KEYWORDS) and col_map.topic is None:
                col_map.topic = col_idx; matched += 1
            elif _matches(cell, GROUP_KEYWORDS) and col_map.group is None:
                col_map.group = col_idx; matched += 1
            elif _matches(cell, FACULTY_KEYWORDS) and col_map.faculty is None:
                col_map.faculty = col_idx; matched += 1
            elif _matches(cell, ROOM_KEYWORDS) and col_map.room is None:
                col_map.room = col_idx; matched += 1
            elif _matches(cell, NOTES_KEYWORDS) and col_map.notes is None:
                col_map.notes = col_idx; matched += 1

        score = matched + (2 if col_map.has_time_info() else 0) + (1 if col_map.has_content_info() else 0)
        if col_map.has_time_info() and matched >= 2 and score > best[2]:
            best = (row_idx, col_map, score)

    if best[0] >= 0:
        return best[0], best[1]

    # Fallback: first non-empty row, empty map
    for row_idx, row in enumerate(grid):
        if row and any(str(c).strip() for c in row):
            return row_idx, ColumnMap()
    return 0, ColumnMap()


def _is_blank(row: list[str]) -> bool:
    return not row or all(not str(c).strip() for c in row)


def _is_spacer(row: list[str]) -> bool:
    """Single-cell rows or rows where only col-0 is filled are likely headings/spacers."""
    non_empty = [c for c in row if str(c).strip()]
    return len(non_empty) <= 1


def parse_grid(grid: list[list[str]]) -> tuple[ColumnMap, list[RawRow]]:
    """
    Parse a full sheet grid into ColumnMap + list of RawRow.

    Handles blank/spacer rows and cell inheritance (merged-cell emulation).
    """
    if not grid:
        return ColumnMap(), []

    header_idx, col_map = detect_header_row(grid)

    # Calculate the minimum row length needed
    max_col = max(
        (col_map.day or 0),
        (col_map.date or 0),
        (col_map.start_time or 0),
        (col_map.end_time or 0),
        (col_map.combined_time or 0),
        (col_map.subject or 0),
        (col_map.title or 0),
        (col_map.topic or 0),
        (col_map.group or 0),
        (col_map.faculty or 0),
        (col_map.room or 0),
        (col_map.notes or 0),
        0,
    ) + 1

    raw_rows: list[RawRow] = []
    last_day = ""
    last_date_str = ""

    for row_idx, row in enumerate(grid):
        if row_idx <= header_idx:
            continue
        if _is_blank(row):
            continue

        padded = _pad(row, max_col)

        day_val = _get(padded, col_map.day)
        date_val = _get(padded, col_map.date)

        # Propagate inherited values from merged/blank cells
        if not day_val and last_day:
            day_val = last_day
        elif day_val:
            last_day = day_val

        if not date_val and last_date_str:
            date_val = last_date_str
        elif date_val:
            last_date_str = date_val

        # Parse time
        start_time_str = ""
        end_time_str = ""

        if col_map.combined_time is not None:
            combined = _get(padded, col_map.combined_time)
            if combined:
                start_time_str, end_time_str = parse_combined_time(combined)
        elif col_map.start_time is not None:
            start_time_str = _get(padded, col_map.start_time)
            end_time_str = _get(padded, col_map.end_time)

        if not start_time_str:
            # Try to find any cell in this row that looks like a time range
            for cell in padded:
                cell_str = str(cell).strip()
                if re.search(r"\d{1,2}:\d{2}\s*[-\u2013]\s*\d{1,2}:\d{2}", cell_str):
                    start_time_str, end_time_str = parse_combined_time(cell_str)
                    break

        if not start_time_str:
            continue  # No time info — skip row

        raw_rows.append(
            RawRow(
                row_index=row_idx + 1,
                values=list(row),
                day=day_val,
                date_str=date_val,
                start_time_str=start_time_str or "",
                end_time_str=end_time_str or "",
                subject=_get(padded, col_map.subject),
                title=_get(padded, col_map.title),
                topic=_get(padded, col_map.topic),
                group=_get(padded, col_map.group),
                faculty=_get(padded, col_map.faculty),
                room=_get(padded, col_map.room),
                notes=_get(padded, col_map.notes),
            )
        )

    return col_map, raw_rows

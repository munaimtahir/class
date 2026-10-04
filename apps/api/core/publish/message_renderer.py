"""Combined day message renderer for the single_day_combined_message posting template."""

from datetime import date, time
from typing import Any, Optional

from .title_builder import SessionDisplayTitleBuilder


# ─── Date / time formatters ───────────────────────────────────────────────────


def _to_time(t) -> time:
    """Coerce a value to a :class:`datetime.time` object."""
    if isinstance(t, time):
        return t
    if isinstance(t, str):
        parts = t.split(":")
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
        return time(h, m)
    raise ValueError(f"Cannot convert {t!r} to time")


def _format_time_str(t) -> tuple[str, str]:
    """Return ``(display_string, period)`` e.g. ``('8:00', 'am')``."""
    t = _to_time(t)
    h, m = t.hour, t.minute
    period = "am" if h < 12 else "pm"
    h12 = h % 12 or 12
    return f"{h12}:{m:02d}", period


def format_time_range(start_t, end_t) -> str:
    """Format a time range as ``'8:00 – 9:30am'`` or ``'11:15am – 1:15pm'``.

    When both times share the same AM/PM period the suffix appears only at the
    end.  When they cross noon the suffix is appended to each.
    """
    start_str, start_period = _format_time_str(start_t)
    end_str, end_period = _format_time_str(end_t)

    if start_period == end_period:
        return f"{start_str} \u2013 {end_str}{end_period}"
    return f"{start_str}{start_period} \u2013 {end_str}{end_period}"


def format_date(d, include_year: bool = False) -> str:
    """Format a date as ``'Tuesday, March 10'`` (or with year)."""
    if isinstance(d, str):
        from datetime import date as _date
        d = _date.fromisoformat(d)
    day_name = d.strftime("%A")
    month_name = d.strftime("%B")
    day_num = d.day
    if include_year:
        return f"{day_name}, {month_name} {day_num}, {d.year}"
    return f"{day_name}, {month_name} {day_num}"


def format_date_time_line(session_date, start_time, end_time, include_year: bool = False) -> str:
    """Return the second line of a session block, e.g.
    ``'Tuesday, March 10 · 8:00 – 9:30am'``."""
    date_str = format_date(session_date, include_year)
    time_range = format_time_range(start_time, end_time)
    return f"{date_str} \u00b7 {time_range}"


# ─── Renderer ────────────────────────────────────────────────────────────────


class CombinedDayMessageRenderer:
    """Render a list of sessions as one combined plain-text announcement."""

    def render(self, sessions: list, options: Optional[dict] = None) -> dict[str, Any]:
        """Render *sessions* using *options* and return a result dict.

        Options (all optional, shown with defaults):
            include_year (bool, False)
            include_video_label (bool, True)
            sort_by_time (bool, True)
            include_day_heading (bool, False)

        Returns::

            {
                "template": "single_day_combined_message",
                "session_count": <int>,
                "skipped_count": <int>,
                "warnings": [...],
                "skipped": [...],
                "message": "<plain text>",
            }
        """
        opts = options or {}
        include_year = bool(opts.get("include_year", False))
        include_video_label = bool(opts.get("include_video_label", True))
        sort_by_time = bool(opts.get("sort_by_time", True))
        include_day_heading = bool(opts.get("include_day_heading", False))

        valid: list[tuple] = []
        skipped: list[dict] = []
        warnings: list[dict] = []
        seen_keys: set = set()

        for s in sessions:
            title = SessionDisplayTitleBuilder.build(s)
            if not title:
                skipped.append({"session_id": getattr(s, "id", None), "reason": "missing title"})
                continue

            meet_link = (
                getattr(getattr(s, "meet_event", None), "meet_link", "") or ""
            )
            if not meet_link:
                warnings.append(
                    {
                        "session_id": getattr(s, "id", None),
                        "title": title,
                        "warning": "missing meet link",
                    }
                )

            # Deduplicate by (title, date, start_time)
            start_key = _to_time(s.start_time).strftime("%H:%M")
            dedup_key = (title.lower(), str(s.date), start_key)
            if dedup_key in seen_keys:
                skipped.append({"session_id": getattr(s, "id", None), "reason": "duplicate"})
                continue
            seen_keys.add(dedup_key)

            valid.append((s, title, meet_link))

        if sort_by_time:
            valid.sort(key=lambda x: (_to_time(x[0].start_time), x[1]))

        blocks: list[str] = []
        for session, title, meet_link in valid:
            date_time_line = format_date_time_line(
                session.date, session.start_time, session.end_time, include_year
            )
            lines = [title, date_time_line]
            if include_video_label:
                link_text = meet_link if meet_link else "(meet link not set)"
                lines.append(f"Video call link: {link_text}")
            elif meet_link:
                lines.append(meet_link)
            blocks.append("\n".join(lines))

        message = "\n\n".join(blocks)

        if include_day_heading and valid:
            first_date = valid[0][0].date
            day_name = format_date(first_date, include_year=False).split(",")[0]  # e.g. "Tuesday"
            month_day = format_date(first_date, include_year=False).split(", ", 1)[1]  # "March 10"
            heading = f"{day_name} timetable \u2014 {month_day}"
            message = heading + "\n\n" + message

        return {
            "template": "single_day_combined_message",
            "session_count": len(valid),
            "skipped_count": len(skipped),
            "warnings": warnings,
            "skipped": skipped,
            "message": message,
        }

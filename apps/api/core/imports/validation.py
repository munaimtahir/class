"""Row-level validation for normalised session dicts."""

from datetime import datetime
from typing import Any

from .dedupe import compute_dedupe_hash


def validate_session_row(
    row_data: dict[str, Any],
    existing_hashes: set[str],
    batch_hashes: set[str],
) -> dict:
    """
    Validate a normalised session row and check for duplicates.

    Mutates row_data to add 'dedupe_hash' when the row is valid.

    Returns:
        {
            "status": "valid" | "invalid" | "duplicate",
            "errors": list[str],
        }

    Side-effect: adds hash to batch_hashes for intra-batch duplicate detection.
    """
    errors: list[str] = []

    # --- Required field checks ---
    if not row_data.get("date"):
        errors.append("Date could not be resolved. Check the Day or Date column value for this row.")

    if not row_data.get("start_time"):
        errors.append("Start time is missing or invalid. Check the Time or Start Time column.")

    if not row_data.get("end_time"):
        errors.append("End time is missing or invalid. Check the Time or End Time column.")

    # --- Time logic ---
    if row_data.get("start_time") and row_data.get("end_time") and not errors:
        try:
            start = datetime.strptime(row_data["start_time"], "%H:%M").time()
            end = datetime.strptime(row_data["end_time"], "%H:%M").time()
            if end <= start:
                errors.append(
                    f"End time ({row_data['end_time']}) must be after "
                    f"start time ({row_data['start_time']})."
                )
        except ValueError:
            errors.append("Time format is invalid. Use HH:MM, for example 09:40.")

    # --- Content ---
    if not row_data.get("title"):
        errors.append(
            "Title could not be built for this row. Fill Title directly or provide Subject or Topic."
        )

    # --- Course ---
    if not row_data.get("course_map_id"):
        errors.append(
            "Course is not resolved for this row. Choose a Default Course before previewing."
        )

    if errors:
        return {"status": "invalid", "errors": errors}

    # --- Deduplicate ---
    h = compute_dedupe_hash(
        course_id=row_data.get("course_map_id"),
        date=row_data.get("date"),
        start_time=row_data.get("start_time"),
        title=row_data.get("title"),
        subgroup_label=row_data.get("subgroup_label", ""),
        publish_mode=row_data.get("publish_mode", "scheduled"),
    )
    row_data["dedupe_hash"] = h

    if h in existing_hashes:
        return {
            "status": "duplicate",
            "errors": ["This row matches an existing session draft already saved in the system."],
        }

    if h in batch_hashes:
        return {
            "status": "duplicate",
            "errors": ["This session appears more than once in the uploaded file or selected sheet."],
        }

    batch_hashes.add(h)
    return {"status": "valid", "errors": []}

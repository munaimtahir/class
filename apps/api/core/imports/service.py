"""
Main import orchestration service.

Provides:
  GoogleSheetImportService.preview()  — fetch, parse, validate; no DB writes
  FileImportService.preview()         — parse uploaded CSV/TSV; no DB writes
  GoogleSheetImportService.commit()   — persist ImportBatch + SessionDraft records
"""

import csv
import io
import uuid

from django.core.cache import cache
from django.db import transaction
from openpyxl import load_workbook

from ..models import Course, ImportBatch, Session, SessionDraft
from .day_extractor import DayResolutionError, filter_rows_by_day, resolve_target_date
from .grid_parser import ColumnMap, parse_grid
from .session_normalizer import normalize_row
from .sheet_client import SheetAccessError, SheetsClient
from .sheet_url_parser import SheetUrlParseError, parse_sheet_url
from .validation import validate_session_row
from ..google_scopes import GoogleScopeMissingError

PREVIEW_CACHE_TTL = 900  # 15 minutes


class ImportServiceError(Exception):
    """Operator-visible import failure."""

    def __init__(self, message: str, code: str = "import_error"):
        super().__init__(message)
        self.code = code


class GoogleSheetImportService:
    def __init__(self, user):
        self.user = user

    def _validate_column_map(self, col_map: ColumnMap):
        problems: list[str] = []
        if col_map.day is None and col_map.date is None:
            problems.append("missing a Day or Date column")
        if not col_map.has_time_info():
            problems.append("missing a Time column or Start Time / End Time columns")
        if not col_map.has_content_info():
            problems.append("missing at least one of Subject, Title, or Topic columns")

        if problems:
            raise ImportServiceError(
                "Could not understand the file layout: " + "; ".join(problems) + ".",
                "missing_required_columns",
            )

    def _build_preview_payload(
        self,
        *,
        raw_rows,
        filtered_rows,
        metadata_title: str,
        selected_sheet: str,
        available_sheets: list[dict],
        target_day: str | None,
        target_date: str | None,
        resolved_date,
        source_ref: str,
        source_type: str,
        spreadsheet_id: str = "",
        default_course_map_id: int | None = None,
    ) -> dict:
        # Validate course ownership
        course: Course | None = None
        if default_course_map_id:
            try:
                course = Course.objects.get(id=default_course_map_id, user=self.user)
            except Course.DoesNotExist:
                raise ImportServiceError(
                    f"Course with id={default_course_map_id} not found or does not belong to you.",
                    "course_not_found",
                )

        # Normalise each row
        weekday_name = None
        if target_day:
            weekday_name = target_day.strip().lower()
        elif resolved_date:
            weekday_name = resolved_date.strftime("%A").lower()

        course_map_id = course.id if course else None
        normalised = [
            normalize_row(row, resolved_date, weekday_name, course_map_id)
            for row in filtered_rows
        ]

        existing_hashes: set[str] = set(
            SessionDraft.objects.filter(
                import_batch__user=self.user
            ).values_list("dedupe_hash", flat=True)
        )

        batch_hashes: set[str] = set()
        sessions_out = []
        valid_count = invalid_count = duplicate_count = 0

        for norm in normalised:
            result = validate_session_row(norm, existing_hashes, batch_hashes)
            status = result["status"]

            sessions_out.append({
                "row_index": norm["row_index"],
                "parsed": {k: v for k, v in norm.items() if k != "row_index"},
                "status": status,
                "errors": result["errors"],
            })

            if status == "valid":
                valid_count += 1
            elif status == "duplicate":
                duplicate_count += 1
            else:
                invalid_count += 1

        preview_token = str(uuid.uuid4())
        payload = {
            "preview_token": preview_token,
            "spreadsheet_title": metadata_title,
            "spreadsheet_id": spreadsheet_id,
            "selected_sheet": selected_sheet,
            "available_sheets": available_sheets,
            "target_day": target_day,
            "target_date": (
                target_date or (resolved_date.isoformat() if resolved_date else None)
            ),
            "summary": {
                "rows_seen": len(raw_rows),
                "filtered_rows": len(filtered_rows),
                "valid_sessions": valid_count,
                "invalid_rows": invalid_count,
                "duplicates": duplicate_count,
            },
            "sessions": sessions_out,
            "source_ref": source_ref,
            "source_type": source_type,
        }
        cache.set(f"sheet_preview:{preview_token}", payload, PREVIEW_CACHE_TTL)
        return payload

    # ------------------------------------------------------------------
    # PREVIEW
    # ------------------------------------------------------------------

    def preview(
        self,
        sheet_url: str,
        target_day: str | None = None,
        target_date: str | None = None,
        sheet_name: str | None = None,
        default_course_map_id: int | None = None,
    ) -> dict:
        """
        Fetch and parse a Google Sheet; return a full preview payload.
        Nothing is written to the database.
        """
        # 1. Parse the URL
        try:
            parsed_url = parse_sheet_url(sheet_url)
        except SheetUrlParseError as exc:
            raise ImportServiceError(str(exc), "invalid_url") from exc

        # 2. Resolve day/date
        try:
            resolved_date, weekday_name = resolve_target_date(target_day, target_date)
        except DayResolutionError as exc:
            raise ImportServiceError(str(exc), "invalid_day") from exc

        # 3. Connect to Sheets API
        client = SheetsClient(self.user)

        # 4. Fetch spreadsheet metadata
        try:
            metadata = client.get_spreadsheet_metadata(parsed_url.spreadsheet_id)
        except SheetAccessError as exc:
            raise ImportServiceError(str(exc), "sheet_access") from exc

        # 5. Resolve which tab to read
        try:
            resolved_sheet_name = client.resolve_sheet_name(
                metadata,
                gid=parsed_url.gid,
                sheet_name=sheet_name,
            )
        except SheetAccessError as exc:
            raise ImportServiceError(str(exc), "sheet_tab") from exc

        # 6. Fetch cell values
        try:
            values = client.get_sheet_values(parsed_url.spreadsheet_id, resolved_sheet_name)
        except SheetAccessError as exc:
            raise ImportServiceError(str(exc), "sheet_read") from exc

        if not values:
            raise ImportServiceError(
                "The selected sheet tab is empty.", "empty_sheet"
            )

        # 7. Parse the grid
        col_map, raw_rows = parse_grid(values)
        self._validate_column_map(col_map)

        # 8. Filter by target day
        if resolved_date or weekday_name:
            filtered_rows = filter_rows_by_day(raw_rows, resolved_date, weekday_name)
        else:
            filtered_rows = raw_rows

        if not filtered_rows:
            day_desc = (
                str(resolved_date) if resolved_date else (weekday_name or "selected day")
            )
            raise ImportServiceError(
                f"No sessions found for {day_desc}. "
                "Check the sheet layout or try a different tab / day.",
                "no_sessions",
            )

        return self._build_preview_payload(
            raw_rows=raw_rows,
            filtered_rows=filtered_rows,
            metadata_title=metadata.get("properties", {}).get("title", ""),
            selected_sheet=resolved_sheet_name,
            available_sheets=client.list_sheets(metadata),
            target_day=target_day,
            target_date=target_date,
            resolved_date=resolved_date,
            source_ref=sheet_url,
            source_type=ImportBatch.SOURCE_GOOGLE_SHEET,
            spreadsheet_id=parsed_url.spreadsheet_id,
            default_course_map_id=default_course_map_id,
        )

    # ------------------------------------------------------------------
    # COMMIT
    # ------------------------------------------------------------------

    @transaction.atomic
    def commit(
        self,
        preview_token: str,
        accepted_row_indices: list[int] | None = None,
    ) -> dict:
        """
        Persist an ImportBatch and SessionDraft records for all valid rows.

        accepted_row_indices: if provided, only commit rows whose row_index is
        in the list; useful when the operator deselects some rows before saving.
        """
        cached = cache.get(f"sheet_preview:{preview_token}")
        if not cached:
            raise ImportServiceError(
                "Preview has expired (15-minute window). Please re-preview the sheet.",
                "preview_expired",
            )

        sessions = cached["sessions"]
        to_commit = [s for s in sessions if s["status"] == "valid"]

        if accepted_row_indices is not None:
            to_commit = [s for s in to_commit if s["row_index"] in accepted_row_indices]

        skipped_dupes = [s for s in sessions if s["status"] == "duplicate"]
        invalid_rows = [s for s in sessions if s["status"] == "invalid"]

        if not to_commit:
            batch_status = ImportBatch.STATUS_FAILED
        elif invalid_rows or skipped_dupes:
            batch_status = ImportBatch.STATUS_PARTIAL
        else:
            batch_status = ImportBatch.STATUS_SUCCESS

        # Parse target_date string to date object for batch
        from datetime import date as date_type

        raw_target_date = cached.get("target_date")
        target_date_obj = None
        if raw_target_date:
            try:
                target_date_obj = date_type.fromisoformat(raw_target_date)
            except (ValueError, TypeError):
                pass

        batch = ImportBatch.objects.create(
            user=self.user,
            source_type=cached.get("source_type", ImportBatch.SOURCE_GOOGLE_SHEET),
            source_ref=cached["source_ref"],
            spreadsheet_id=cached["spreadsheet_id"],
            sheet_name=cached["selected_sheet"],
            target_date=target_date_obj,
            row_count=cached["summary"]["rows_seen"],
            valid_count=len(to_commit),
            invalid_count=len(invalid_rows),
            duplicate_count=len(skipped_dupes),
            status=batch_status,
            diagnostics_json={
                "invalid_rows": invalid_rows,
                "duplicate_rows": skipped_dupes,
            },
        )

        created_ids = []
        for s in to_commit:
            parsed = s["parsed"]
            course: Course | None = None
            course_map_id = parsed.get("course_map_id")
            if course_map_id:
                try:
                    course = Course.objects.get(id=course_map_id, user=self.user)
                except Course.DoesNotExist:
                    pass

            draft = SessionDraft.objects.create(
                import_batch=batch,
                course=course,
                date=parsed["date"],
                start_time=parsed["start_time"],
                end_time=parsed["end_time"],
                title=parsed["title"],
                subject=parsed.get("subject", ""),
                topic=parsed.get("topic", ""),
                subgroup_label=parsed.get("subgroup_label", ""),
                requires_meet=parsed.get("requires_meet", True),
                publish_mode=parsed.get("publish_mode", "scheduled"),
                scheduled_for=parsed.get("scheduled_for"),
                topic_label=parsed.get("topic_label", ""),
                notes=parsed.get("notes", ""),
                dedupe_hash=parsed.get("dedupe_hash", ""),
                status=SessionDraft.STATUS_ACCEPTED,
                row_index=s["row_index"],
            )
            created_ids.append(draft.id)

        cache.delete(f"sheet_preview:{preview_token}")

        return {
            "batch_id": batch.id,
            "status": batch_status,
            "created": len(created_ids),
            "skipped_duplicates": len(skipped_dupes),
            "invalid_rows": len(invalid_rows),
            "session_draft_ids": created_ids,
        }

    # ------------------------------------------------------------------
    # PROMOTE
    # ------------------------------------------------------------------

    @transaction.atomic
    def promote_batch(self, batch_id: int) -> dict:
        """
        Convert all accepted SessionDraft records in a batch to live Session records.

        Drafts already promoted are skipped.  After promotion the Session records
        are in status='pending', ready for the existing publish pipeline.
        """
        try:
            batch = ImportBatch.objects.get(id=batch_id, user=self.user)
        except ImportBatch.DoesNotExist:
            raise ImportServiceError(
                f"Import batch {batch_id} not found.", "batch_not_found"
            )

        drafts = batch.session_drafts.filter(
            status=SessionDraft.STATUS_ACCEPTED, promoted_session__isnull=True
        ).select_related("course")

        promoted_ids = []
        for draft in drafts:
            if draft.course is None:
                continue  # Cannot promote without a course

            session = Session.objects.create(
                course=draft.course,
                date=draft.date,
                start_time=draft.start_time,
                end_time=draft.end_time,
                title=draft.title,
                topic=draft.topic or draft.topic_label,
                subject=draft.subject,
                group=draft.subgroup_label,
                meet_required=draft.requires_meet,
                post_type=Session.POST_TYPE_MATERIAL,
                status=Session.STATUS_PENDING,
            )
            draft.promoted_session = session
            draft.status = SessionDraft.STATUS_PROMOTED
            draft.save(update_fields=["promoted_session", "status"])
            promoted_ids.append(session.id)

        return {
            "batch_id": batch.id,
            "promoted": len(promoted_ids),
            "session_ids": promoted_ids,
        }


class FileImportService(GoogleSheetImportService):
    """CSV/TSV upload import using the same parsing and validation pipeline."""

    def preview(
        self,
        *,
        file_name: str,
        file_bytes: bytes,
        target_day: str | None = None,
        target_date: str | None = None,
        default_course_map_id: int | None = None,
    ) -> dict:
        try:
            resolved_date, weekday_name = resolve_target_date(target_day, target_date)
        except DayResolutionError as exc:
            raise ImportServiceError(str(exc), "invalid_day") from exc

        if not file_bytes:
            raise ImportServiceError("Uploaded file is empty.", "empty_file")

        grid, selected_sheet = self._parse_uploaded_grid(file_name, file_bytes)
        col_map, raw_rows = parse_grid(grid)
        self._validate_column_map(col_map)

        if resolved_date or weekday_name:
            filtered_rows = filter_rows_by_day(raw_rows, resolved_date, weekday_name)
        else:
            filtered_rows = raw_rows

        if not filtered_rows:
            day_desc = (
                str(resolved_date) if resolved_date else (weekday_name or "selected day")
            )
            raise ImportServiceError(
                f"No sessions found for {day_desc}. Check the selected worksheet, day filter, or date column values.",
                "no_sessions",
            )

        return self._build_preview_payload(
            raw_rows=raw_rows,
            filtered_rows=filtered_rows,
            metadata_title=file_name,
            selected_sheet=selected_sheet,
            available_sheets=[],
            target_day=target_day,
            target_date=target_date,
            resolved_date=resolved_date,
            source_ref=file_name,
            source_type=ImportBatch.SOURCE_CSV,
            default_course_map_id=default_course_map_id,
        )

    def _parse_uploaded_grid(self, file_name: str, file_bytes: bytes) -> tuple[list[list[str]], str]:
        lower_name = (file_name or "").lower()
        if lower_name.endswith((".xlsx", ".xlsm")):
            return self._parse_excel_grid(file_name, file_bytes)
        if not lower_name.endswith((".csv", ".tsv", ".txt")):
            raise ImportServiceError(
                "Unsupported file type. Upload CSV, TSV, XLSX, or XLSM.",
                "unsupported_file_type",
            )

        try:
            text = file_bytes.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ImportServiceError(
                "Could not decode the uploaded file. Please save it as UTF-8 CSV/TSV.",
                "invalid_file_encoding",
            ) from exc

        rows = [line for line in text.splitlines() if line.strip()]
        if not rows:
            raise ImportServiceError("Uploaded file is empty.", "empty_file")

        sample = "\n".join(rows[:5])
        delimiter = ","
        if lower_name.endswith(".tsv"):
            delimiter = "\t"
        else:
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",\t;")
                delimiter = dialect.delimiter
            except csv.Error:
                delimiter = "\t" if "\t" in sample and sample.count("\t") > sample.count(",") else ","

        reader = csv.reader(io.StringIO(text), delimiter=delimiter)
        grid = [[cell.strip() for cell in row] for row in reader]
        if not any(any(cell for cell in row) for row in grid):
            raise ImportServiceError("Uploaded file is empty.", "empty_file")
        return grid, "Uploaded file"

    def _parse_excel_grid(self, file_name: str, file_bytes: bytes) -> tuple[list[list[str]], str]:
        try:
            workbook = load_workbook(io.BytesIO(file_bytes), data_only=True, read_only=True)
        except Exception as exc:
            raise ImportServiceError(
                "Could not read the Excel file. Please upload a valid XLSX/XLSM workbook.",
                "invalid_excel_file",
            ) from exc

        if not workbook.worksheets:
            raise ImportServiceError("The uploaded workbook has no worksheets.", "empty_workbook")

        worksheet = None
        for candidate in workbook.worksheets:
            rows = list(candidate.iter_rows(values_only=True))
            if any(any(cell not in (None, "") for cell in row) for row in rows):
                worksheet = candidate
                break

        if worksheet is None:
            raise ImportServiceError("The uploaded workbook has no data rows.", "empty_workbook")

        grid: list[list[str]] = []
        for row in worksheet.iter_rows(values_only=True):
            grid.append([
                "" if cell is None else str(cell).strip()
                for cell in row
            ])

        return grid, worksheet.title

import io
from datetime import date, time
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from openpyxl import Workbook
from rest_framework.test import APIClient

from .imports.day_extractor import (
    DayResolutionError,
    filter_rows_by_day,
    parse_row_date,
    resolve_target_date,
)
from .imports.dedupe import compute_dedupe_hash
from .imports.grid_parser import (
    ColumnMap,
    RawRow,
    detect_header_row,
    parse_combined_time,
    parse_grid,
)
from .imports.session_normalizer import build_title, parse_time_str
from .imports.sheet_url_parser import ParsedSheetUrl, SheetUrlParseError, parse_sheet_url
from .imports.validation import validate_session_row
from .google_scopes import (
    GoogleScopeMissingError,
    SCOPE_CALENDAR,
    SCOPE_CLASSROOM_COURSES_READONLY,
    SCOPE_CLASSROOM_COURSEWORK_MATERIALS,
    SCOPE_SPREADSHEETS_READONLY,
    validate_scopes,
)
from .models import Course, ImportBatch, MeetEvent, Session, SessionDraft
from .publish.message_renderer import (
    CombinedDayMessageRenderer,
    format_date,
    format_time_range,
)
from .publish.title_builder import SessionDisplayTitleBuilder
from .tasks import create_classroom_post, generate_meet_link

User = get_user_model()


class GoogleScopeUtilitiesTests(TestCase):
    def test_validate_scopes_returns_missing(self):
        result = validate_scopes(
            [SCOPE_CLASSROOM_COURSES_READONLY],
            [SCOPE_CLASSROOM_COURSES_READONLY, SCOPE_SPREADSHEETS_READONLY],
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.missing, [SCOPE_SPREADSHEETS_READONLY])


class GoogleScopeEnforcementTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="scopeuser@example.com", password="testpass123")
        self.user.google_scopes = ""
        self.user.google_scopes_json = []
        self.user.save(update_fields=["google_scopes", "google_scopes_json"])
        self.client.force_authenticate(self.user)

    @patch("core.google_client.build")
    def test_list_courses_blocks_before_google_call_when_scope_missing(self, build_mock):
        response = self.client.get("/api/classrooms/sync/")
        self.assertEqual(response.status_code, 403)
        payload = response.json()
        self.assertEqual(payload.get("code"), "GOOGLE_SCOPE_MISSING")
        self.assertEqual(payload.get("feature"), "list_courses")
        self.assertIn(SCOPE_CLASSROOM_COURSES_READONLY, payload.get("missingScopes", []))
        build_mock.assert_not_called()

    @patch("core.views.requests.get")
    @patch("core.views.requests.post")
    def test_oauth_callback_persists_scope_metadata(self, post_mock, get_mock):
        post_mock.return_value.status_code = 200
        post_mock.return_value.json.return_value = {
            "access_token": "access-token-1",
            "refresh_token": "refresh-token-1",
            "scope": f"{SCOPE_CLASSROOM_COURSES_READONLY} {SCOPE_SPREADSHEETS_READONLY}",
            "expires_in": 3600,
            "token_type": "Bearer",
            "id_token": "id-token-value",
        }
        get_mock.return_value.status_code = 200
        get_mock.return_value.json.return_value = {
            "email": "oauth-user@example.com",
            "name": "OAuth User",
            "sub": "google-sub-1",
        }

        response = self.client.get("/api/auth/google/callback?code=test-code")
        self.assertEqual(response.status_code, 302)

        user = User.objects.get(email="oauth-user@example.com")
        self.assertIn(SCOPE_CLASSROOM_COURSES_READONLY, user.google_scopes_json)
        self.assertIn(SCOPE_SPREADSHEETS_READONLY, user.google_scopes_json)
        self.assertEqual(user.token_meta_json.get("token_type"), "Bearer")
        self.assertTrue(user.token_meta_json.get("id_token_present"))
        self.assertIsNotNone(user.google_last_refresh_at)


class GenerateMeetFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="owner@example.com", password="testpass123")
        self.other_user = User.objects.create_user(email="other@example.com", password="testpass123")
        self.course = Course.objects.create(
            user=self.user,
            google_course_id="course-1",
            name="Physiology",
        )
        self.other_course = Course.objects.create(
            user=self.other_user,
            google_course_id="course-2",
            name="Other",
        )
        self.session = Session.objects.create(
            course=self.course,
            date=date(2026, 3, 10),
            start_time=time(9, 40),
            end_time=time(10, 40),
            title="Processing of Signals In CNS",
            topic="CNS",
            subject="Physiology",
            meet_required=True,
        )
        self.other_session = Session.objects.create(
            course=self.other_course,
            date=date(2026, 3, 10),
            start_time=time(11, 0),
            end_time=time(12, 0),
            title="Other Session",
            meet_required=True,
        )
        self.client.force_authenticate(self.user)

    @patch("core.views.generate_meet_link.delay")
    def test_generate_meet_only_queues_owned_sessions(self, delay_mock):
        response = self.client.post(
            "/api/sessions/generate-meet/",
            {"session_ids": [self.session.id, self.other_session.id]},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"queued": 1})
        delay_mock.assert_called_once_with(self.session.id)

    @patch("core.tasks.GoogleService.create_meet_event")
    def test_generate_meet_task_persists_event_details(self, create_meet_event_mock):
        create_meet_event_mock.return_value = ("event-123", "https://meet.google.com/abc-defg-hij")

        generate_meet_link(self.session.id)

        meet_event = MeetEvent.objects.get(session=self.session)
        self.assertEqual(meet_event.calendar_event_id, "event-123")
        self.assertEqual(meet_event.meet_link, "https://meet.google.com/abc-defg-hij")

    @patch("core.tasks.GoogleService.create_meet_event")
    def test_session_serializer_includes_meet_fields(self, create_meet_event_mock):
        create_meet_event_mock.return_value = ("event-456", "https://meet.google.com/xyz-abcd-efg")
        generate_meet_link(self.session.id)

        response = self.client.get("/api/sessions/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["calendar_event_id"], "event-456")
        self.assertEqual(payload[0]["meet_link"], "https://meet.google.com/xyz-abcd-efg")

    @patch("core.tasks.GoogleService.create_classroom_material")
    @patch("core.tasks.GoogleService.create_meet_event")
    def test_publish_creates_meet_first_and_includes_link(
        self,
        create_meet_event_mock,
        create_classroom_material_mock,
    ):
        create_meet_event_mock.return_value = ("event-789", "https://meet.google.com/qrs-tuvw-xyz")
        create_classroom_material_mock.return_value = "post-123"

        create_classroom_post(self.session.id, publish_now=True)

        create_classroom_material_mock.assert_called_once()

    @patch("core.tasks.GoogleService.create_meet_event")
    def test_generate_meet_marks_failed_on_missing_calendar_scope(self, create_meet_event_mock):
        create_meet_event_mock.side_effect = GoogleScopeMissingError(
            feature="create_calendar_event",
            missing_scopes=[SCOPE_CALENDAR],
        )

        with self.assertRaises(GoogleScopeMissingError):
            generate_meet_link(self.session.id)

        self.session.refresh_from_db()
        self.assertEqual(self.session.status, Session.STATUS_FAILED)

    @patch("core.tasks.GoogleService.create_meet_event")
    @patch("core.tasks.GoogleService.create_classroom_material")
    def test_publish_marks_failed_on_missing_material_scope(
        self,
        create_classroom_material_mock,
        create_meet_event_mock,
    ):
        create_meet_event_mock.return_value = ("event-111", "https://meet.google.com/ok-scope")
        create_classroom_material_mock.side_effect = GoogleScopeMissingError(
            feature="create_course_material",
            missing_scopes=[SCOPE_CLASSROOM_COURSEWORK_MATERIALS],
        )

        with self.assertRaises(GoogleScopeMissingError):
            create_classroom_post(self.session.id, publish_now=True)

        self.session.refresh_from_db()
        self.assertEqual(self.session.status, Session.STATUS_FAILED)
        self.assertEqual(
            create_classroom_material_mock.call_args.kwargs["meet_link"],
            "https://meet.google.com/ok-scope",
        )
        meet_event = MeetEvent.objects.get(session=self.session)
        self.assertEqual(meet_event.calendar_event_id, "event-111")


class AdminStaticFilesTests(TestCase):
    def test_admin_base_css_is_served_when_debug_is_disabled(self):
        with self.settings(DEBUG=False):
            response = self.client.get("/static/admin/css/base.css")

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/css", response["Content-Type"])


# ---------------------------------------------------------------------------
# Unit tests — sheet URL parser
# ---------------------------------------------------------------------------

class SheetUrlParserTests(TestCase):
    def test_standard_edit_url(self):
        url = "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms/edit"
        parsed = parse_sheet_url(url)
        self.assertEqual(parsed.spreadsheet_id, "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms")
        self.assertIsNone(parsed.gid)

    def test_url_with_gid(self):
        url = "https://docs.google.com/spreadsheets/d/ABCDEF123/edit#gid=456789"
        parsed = parse_sheet_url(url)
        self.assertEqual(parsed.spreadsheet_id, "ABCDEF123")
        self.assertEqual(parsed.gid, "456789")

    def test_url_with_query_gid(self):
        url = "https://docs.google.com/spreadsheets/d/SHEETID/pub?gid=999"
        parsed = parse_sheet_url(url)
        self.assertEqual(parsed.spreadsheet_id, "SHEETID")
        self.assertEqual(parsed.gid, "999")

    def test_empty_url_raises(self):
        with self.assertRaises(SheetUrlParseError):
            parse_sheet_url("")

    def test_non_sheets_url_raises(self):
        with self.assertRaises(SheetUrlParseError):
            parse_sheet_url("https://example.com/not-a-sheet")

    def test_url_without_id_segment_raises(self):
        with self.assertRaises(SheetUrlParseError):
            parse_sheet_url("https://docs.google.com/spreadsheets/")


# ---------------------------------------------------------------------------
# Unit tests — time parsing
# ---------------------------------------------------------------------------

class TimeParsingTests(TestCase):
    def test_hhmm_format(self):
        t = parse_time_str("09:40")
        self.assertEqual(t.hour, 9)
        self.assertEqual(t.minute, 40)

    def test_single_digit_hour(self):
        t = parse_time_str("9:05")
        self.assertIsNotNone(t)
        self.assertEqual(t.hour, 9)

    def test_combined_time_hyphen(self):
        start, end = parse_combined_time("09:40-10:30")
        self.assertEqual(start, "09:40")
        self.assertEqual(end, "10:30")

    def test_combined_time_spaces(self):
        start, end = parse_combined_time("09:40 - 10:30")
        self.assertEqual(start, "09:40")
        self.assertEqual(end, "10:30")

    def test_combined_time_en_dash(self):
        start, end = parse_combined_time("09:40\u201310:30")
        self.assertEqual(start, "09:40")
        self.assertEqual(end, "10:30")

    def test_invalid_time_returns_none(self):
        self.assertIsNone(parse_time_str("not-a-time"))
        self.assertIsNone(parse_time_str(""))

    def test_combined_no_match_returns_none(self):
        s, e = parse_combined_time("subject")
        self.assertIsNone(s)
        self.assertIsNone(e)


# ---------------------------------------------------------------------------
# Unit tests — weekday / date resolution
# ---------------------------------------------------------------------------

class DayResolutionTests(TestCase):
    def test_resolve_from_iso_date(self):
        resolved, wd = resolve_target_date(target_date="2026-03-10")
        self.assertEqual(resolved, date(2026, 3, 10))
        self.assertEqual(wd, "tuesday")

    def test_resolve_from_weekday_name(self):
        resolved, wd = resolve_target_date(target_day="Tuesday")
        self.assertIsNone(resolved)
        self.assertEqual(wd, "tuesday")

    def test_invalid_date_raises(self):
        with self.assertRaises(DayResolutionError):
            resolve_target_date(target_date="not-a-date")

    def test_unknown_weekday_raises(self):
        with self.assertRaises(DayResolutionError):
            resolve_target_date(target_day="Funday")

    def test_parse_row_date_iso(self):
        self.assertEqual(parse_row_date("2026-03-10"), date(2026, 3, 10))

    def test_parse_row_date_slash(self):
        self.assertEqual(parse_row_date("10/03/2026"), date(2026, 3, 10))

    def test_parse_row_date_invalid(self):
        self.assertIsNone(parse_row_date("not-a-date"))
        self.assertIsNone(parse_row_date(""))


# ---------------------------------------------------------------------------
# Unit tests — header detection and grid parsing
# ---------------------------------------------------------------------------

class GridParserTests(TestCase):
    def _sample_grid(self):
        return [
            ["Day", "Start Time", "End Time", "Subject", "Topic", "Group"],
            ["Tuesday", "09:40", "10:30", "Physiology", "ANS I", "Whole class"],
            ["Tuesday", "10:40", "11:30", "Embryology", "Somites", "Group A"],
            ["Wednesday", "09:40", "10:30", "Pathology", "Inflammation", ""],
        ]

    def test_header_detection(self):
        grid = self._sample_grid()
        header_idx, col_map = detect_header_row(grid)
        self.assertEqual(header_idx, 0)
        self.assertIsNotNone(col_map.start_time)
        self.assertIsNotNone(col_map.end_time)

    def test_parse_grid_returns_rows_after_header(self):
        grid = self._sample_grid()
        col_map, rows = parse_grid(grid)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0].subject, "Physiology")
        self.assertEqual(rows[0].start_time_str, "09:40")
        self.assertEqual(rows[0].end_time_str, "10:30")

    def test_blank_rows_skipped(self):
        grid = self._sample_grid()
        grid.insert(2, [])  # blank row after header
        _, rows = parse_grid(grid)
        self.assertEqual(len(rows), 3)

    def test_combined_time_column(self):
        grid = [
            ["Day", "Time", "Subject", "Topic"],
            ["Tuesday", "09:40-10:30", "Physiology", "ANS"],
        ]
        _, rows = parse_grid(grid)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].start_time_str, "09:40")
        self.assertEqual(rows[0].end_time_str, "10:30")

    def test_inherited_day_from_blank_cell(self):
        grid = [
            ["Day", "Start Time", "End Time", "Subject"],
            ["Tuesday", "09:40", "10:30", "Physiology"],
            ["", "10:40", "11:30", "Embryology"],  # blank Day cell
        ]
        _, rows = parse_grid(grid)
        self.assertEqual(rows[1].day, "Tuesday")


# ---------------------------------------------------------------------------
# Unit tests — row filtering by day
# ---------------------------------------------------------------------------

class DayFilterTests(TestCase):
    def _make_row(self, day="", date_str="", row_index=1):
        return RawRow(
            row_index=row_index, day=day, date_str=date_str,
            start_time_str="09:40", end_time_str="10:30",
        )

    def test_filter_by_date(self):
        rows = [
            self._make_row(date_str="2026-03-10", row_index=1),
            self._make_row(date_str="2026-03-11", row_index=2),
        ]
        result = filter_rows_by_day(rows, date(2026, 3, 10), "tuesday")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].row_index, 1)

    def test_filter_by_weekday_name(self):
        rows = [
            self._make_row(day="Tuesday", row_index=1),
            self._make_row(day="Wednesday", row_index=2),
            self._make_row(day="Tuesday", row_index=3),
        ]
        result = filter_rows_by_day(rows, None, "tuesday")
        self.assertEqual(len(result), 2)

    def test_no_filter_returns_all(self):
        rows = [self._make_row(row_index=i) for i in range(5)]
        result = filter_rows_by_day(rows, None, None)
        self.assertEqual(len(result), 5)


# ---------------------------------------------------------------------------
# Unit tests — title building
# ---------------------------------------------------------------------------

class TitleBuildingTests(TestCase):
    def test_title_from_title_field(self):
        row = RawRow(row_index=1, title="Physiology Lec-12")
        self.assertEqual(build_title(row), "Physiology Lec-12")

    def test_title_from_subject_and_topic(self):
        row = RawRow(row_index=1, subject="Physiology", topic="ANS I")
        self.assertEqual(build_title(row), "Physiology — ANS I")

    def test_title_from_subject_only(self):
        row = RawRow(row_index=1, subject="Anatomy")
        self.assertEqual(build_title(row), "Anatomy")

    def test_empty_row_gives_empty_title(self):
        row = RawRow(row_index=1)
        self.assertEqual(build_title(row), "")


# ---------------------------------------------------------------------------
# Unit tests — dedupe hash
# ---------------------------------------------------------------------------

class DedupeHashTests(TestCase):
    def test_same_inputs_same_hash(self):
        h1 = compute_dedupe_hash(1, "2026-03-10", "09:40", "Physiology Lec-12", "Whole class")
        h2 = compute_dedupe_hash(1, "2026-03-10", "09:40", "Physiology Lec-12", "Whole class")
        self.assertEqual(h1, h2)

    def test_different_date_different_hash(self):
        h1 = compute_dedupe_hash(1, "2026-03-10", "09:40", "Physiology Lec-12")
        h2 = compute_dedupe_hash(1, "2026-03-11", "09:40", "Physiology Lec-12")
        self.assertNotEqual(h1, h2)

    def test_case_insensitive_title(self):
        h1 = compute_dedupe_hash(1, "2026-03-10", "09:40", "Physiology Lec-12")
        h2 = compute_dedupe_hash(1, "2026-03-10", "09:40", "physiology lec-12")
        self.assertEqual(h1, h2)

    def test_hash_is_64_chars(self):
        h = compute_dedupe_hash(1, "2026-03-10", "09:40", "Test")
        self.assertEqual(len(h), 64)


# ---------------------------------------------------------------------------
# Unit tests — row validation
# ---------------------------------------------------------------------------

class RowValidationTests(TestCase):
    def _valid_row(self):
        return {
            "course_map_id": 1,
            "date": "2026-03-10",
            "start_time": "09:40",
            "end_time": "10:30",
            "title": "Physiology Lec-12",
            "subject": "Physiology",
            "subgroup_label": "",
            "publish_mode": "scheduled",
        }

    def test_valid_row_passes(self):
        result = validate_session_row(self._valid_row(), set(), set())
        self.assertEqual(result["status"], "valid")
        self.assertEqual(result["errors"], [])

    def test_missing_date_fails(self):
        row = self._valid_row()
        row["date"] = None
        result = validate_session_row(row, set(), set())
        self.assertEqual(result["status"], "invalid")
        self.assertTrue(any("date" in e.lower() for e in result["errors"]))

    def test_missing_title_fails(self):
        row = self._valid_row()
        row["title"] = ""
        result = validate_session_row(row, set(), set())
        self.assertEqual(result["status"], "invalid")

    def test_end_before_start_fails(self):
        row = self._valid_row()
        row["end_time"] = "08:00"
        result = validate_session_row(row, set(), set())
        self.assertEqual(result["status"], "invalid")
        self.assertTrue(any("end time" in e.lower() for e in result["errors"]))

    def test_duplicate_against_existing_hash(self):
        row = self._valid_row()
        h = compute_dedupe_hash(1, "2026-03-10", "09:40", "Physiology Lec-12")
        result = validate_session_row(row, {h}, set())
        self.assertEqual(result["status"], "duplicate")

    def test_intra_batch_duplicate(self):
        row = self._valid_row()
        batch_hashes: set = set()
        validate_session_row(row, set(), batch_hashes)
        result = validate_session_row(dict(self._valid_row()), set(), batch_hashes)
        self.assertEqual(result["status"], "duplicate")


# ---------------------------------------------------------------------------
# Integration tests — import endpoints
# ---------------------------------------------------------------------------

class ImportEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            email="importer@example.com", password="pass123"
        )
        self.user.google_scopes = (
            "https://www.googleapis.com/auth/spreadsheets.readonly "
            "https://www.googleapis.com/auth/classroom.courses.readonly"
        )
        self.user.save()
        self.course = Course.objects.create(
            user=self.user, google_course_id="c-001", name="Physiology"
        )
        self.client.force_authenticate(self.user)

    def _mock_sheet_data(self):
        return [
            ["Day", "Start Time", "End Time", "Subject", "Topic", "Group"],
            ["Tuesday", "09:40", "10:30", "Physiology", "ANS I", "Whole class"],
            ["Tuesday", "10:40", "11:30", "Embryology", "Somites", "Group A"],
            ["Tuesday", "11:40", "12:30", "Pathology", "Inflammation", ""],
            ["Wednesday", "09:40", "10:30", "Anatomy", "Bones", ""],
        ]

    @patch("core.imports.service.SheetsClient")
    def test_preview_returns_valid_sessions(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get_spreadsheet_metadata.return_value = {
            "spreadsheetId": "SHEETID",
            "properties": {"title": "MBBS Timetable"},
            "sheets": [{"properties": {"sheetId": 0, "title": "Week 3", "index": 0}}],
        }
        mock_client.resolve_sheet_name.return_value = "Week 3"
        mock_client.get_sheet_values.return_value = self._mock_sheet_data()
        mock_client.list_sheets.return_value = [{"title": "Week 3", "gid": 0}]

        resp = self.client.post(
            "/api/imports/google-sheet/preview",
            {
                "sheet_url": "https://docs.google.com/spreadsheets/d/SHEETID/edit",
                "target_date": "2026-03-10",
                "default_course_map_id": self.course.id,
            },
            format="json",
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["spreadsheet_title"], "MBBS Timetable")
        self.assertIn("preview_token", data)
        # Only Tuesday rows (rows 2–4) should be returned as valid
        valid = [s for s in data["sessions"] if s["status"] == "valid"]
        self.assertEqual(len(valid), 3)
        self.assertEqual(data["summary"]["valid_sessions"], 3)

    @patch("core.imports.service.SheetsClient")
    def test_commit_creates_import_batch_and_drafts(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get_spreadsheet_metadata.return_value = {
            "spreadsheetId": "SHEETID",
            "properties": {"title": "MBBS Timetable"},
            "sheets": [{"properties": {"sheetId": 0, "title": "Week 3", "index": 0}}],
        }
        mock_client.resolve_sheet_name.return_value = "Week 3"
        mock_client.get_sheet_values.return_value = self._mock_sheet_data()
        mock_client.list_sheets.return_value = [{"title": "Week 3", "gid": 0}]

        preview_resp = self.client.post(
            "/api/imports/google-sheet/preview",
            {
                "sheet_url": "https://docs.google.com/spreadsheets/d/SHEETID/edit",
                "target_date": "2026-03-10",
                "default_course_map_id": self.course.id,
            },
            format="json",
        )
        token = preview_resp.json()["preview_token"]

        commit_resp = self.client.post(
            "/api/imports/google-sheet/commit",
            {"preview_token": token},
            format="json",
        )

        self.assertEqual(commit_resp.status_code, 201)
        result = commit_resp.json()
        self.assertEqual(result["created"], 3)
        self.assertEqual(ImportBatch.objects.filter(user=self.user).count(), 1)
        self.assertEqual(SessionDraft.objects.filter(import_batch__user=self.user).count(), 3)

    @patch("core.imports.service.SheetsClient")
    def test_duplicate_prevention_on_reimport(self, mock_client_cls):
        """Re-importing the same sheet should not create duplicate drafts."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get_spreadsheet_metadata.return_value = {
            "spreadsheetId": "SHEETID",
            "properties": {"title": "MBBS Timetable"},
            "sheets": [{"properties": {"sheetId": 0, "title": "Week 3", "index": 0}}],
        }
        mock_client.resolve_sheet_name.return_value = "Week 3"
        mock_client.get_sheet_values.return_value = self._mock_sheet_data()
        mock_client.list_sheets.return_value = [{"title": "Week 3", "gid": 0}]

        params = {
            "sheet_url": "https://docs.google.com/spreadsheets/d/SHEETID/edit",
            "target_date": "2026-03-10",
            "default_course_map_id": self.course.id,
        }

        # First import
        p1 = self.client.post("/api/imports/google-sheet/preview", params, format="json")
        self.client.post(
            "/api/imports/google-sheet/commit",
            {"preview_token": p1.json()["preview_token"]},
            format="json",
        )

        # Second import of the same sheet
        p2 = self.client.post("/api/imports/google-sheet/preview", params, format="json")
        data = p2.json()
        duplicates = [s for s in data["sessions"] if s["status"] == "duplicate"]
        self.assertEqual(len(duplicates), 3)
        self.assertEqual(data["summary"]["duplicates"], 3)

    @patch("core.imports.service.SheetsClient")
    def test_promote_creates_session_records(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get_spreadsheet_metadata.return_value = {
            "spreadsheetId": "SHEETID",
            "properties": {"title": "MBBS Timetable"},
            "sheets": [{"properties": {"sheetId": 0, "title": "Week 3", "index": 0}}],
        }
        mock_client.resolve_sheet_name.return_value = "Week 3"
        mock_client.get_sheet_values.return_value = self._mock_sheet_data()
        mock_client.list_sheets.return_value = [{"title": "Week 3", "gid": 0}]

        p = self.client.post(
            "/api/imports/google-sheet/preview",
            {
                "sheet_url": "https://docs.google.com/spreadsheets/d/SHEETID/edit",
                "target_date": "2026-03-10",
                "default_course_map_id": self.course.id,
            },
            format="json",
        )
        c = self.client.post(
            "/api/imports/google-sheet/commit",
            {"preview_token": p.json()["preview_token"]},
            format="json",
        )
        batch_id = c.json()["batch_id"]

        promote_resp = self.client.post(f"/api/imports/{batch_id}/promote/")
        self.assertEqual(promote_resp.status_code, 200)
        result = promote_resp.json()
        self.assertEqual(result["promoted"], 3)
        # Sessions should now be accessible via the sessions list endpoint
        sessions_resp = self.client.get("/api/sessions/")
        self.assertEqual(sessions_resp.status_code, 200)
        # There should be 3 new sessions (plus the 2 from GenerateMeetFlowTests.setUp if run together)
        promoted_ids = set(result["session_ids"])
        returned_ids = {s["id"] for s in sessions_resp.json()}
        self.assertTrue(promoted_ids.issubset(returned_ids))

    def test_preview_with_invalid_url(self):
        resp = self.client.post(
            "/api/imports/google-sheet/preview",
            {"sheet_url": "https://example.com/not-a-sheet"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("detail", resp.json())

    def test_commit_without_token_returns_400(self):
        resp = self.client.post(
            "/api/imports/google-sheet/commit",
            {},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_missing_sheets_scope_returns_403(self):
        """User without the Sheets scope should get a clear error."""
        User = get_user_model()
        limited_user = User.objects.create_user(
            email="noscope@example.com", password="pass123"
        )
        limited_user.google_scopes = "https://www.googleapis.com/auth/classroom.courses.readonly"
        limited_user.save()
        client = APIClient()
        client.force_authenticate(limited_user)

        resp = client.post(
            "/api/imports/google-sheet/preview",
            {"sheet_url": "https://docs.google.com/spreadsheets/d/SHEETID/edit"},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)
        payload = resp.json()
        self.assertEqual(payload.get("code"), "GOOGLE_SCOPE_MISSING")
        self.assertEqual(payload.get("feature"), "import_google_sheet_preview")
        self.assertIn("reauthorizeUrl", payload)

    def test_file_preview_returns_valid_sessions(self):
        uploaded = SimpleUploadedFile(
            "timetable.csv",
            (
                "Day,Start Time,End Time,Subject,Topic,Group\n"
                "Tuesday,09:40,10:30,Physiology,ANS I,Whole class\n"
                "Tuesday,10:40,11:30,Embryology,Somites,Group A\n"
            ).encode("utf-8"),
            content_type="text/csv",
        )

        resp = self.client.post(
            "/api/imports/file/preview",
            {
                "file": uploaded,
                "target_date": "2026-03-10",
                "default_course_map_id": str(self.course.id),
            },
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["spreadsheet_title"], "timetable.csv")
        self.assertEqual(data["selected_sheet"], "Uploaded file")
        self.assertEqual(data["summary"]["valid_sessions"], 2)

    def test_file_preview_then_commit_creates_csv_import_batch(self):
        uploaded = SimpleUploadedFile(
            "timetable.csv",
            (
                "Day,Start Time,End Time,Subject,Topic,Group\n"
                "Tuesday,09:40,10:30,Physiology,ANS I,Whole class\n"
                "Tuesday,10:40,11:30,Embryology,Somites,Group A\n"
            ).encode("utf-8"),
            content_type="text/csv",
        )

        preview_resp = self.client.post(
            "/api/imports/file/preview",
            {
                "file": uploaded,
                "target_date": "2026-03-10",
                "default_course_map_id": str(self.course.id),
            },
        )
        self.assertEqual(preview_resp.status_code, 200)

        token = preview_resp.json()["preview_token"]
        commit_resp = self.client.post(
            "/api/imports/google-sheet/commit",
            {"preview_token": token},
            format="json",
        )

        self.assertEqual(commit_resp.status_code, 201)
        batch = ImportBatch.objects.get(user=self.user)
        self.assertEqual(batch.source_type, ImportBatch.SOURCE_CSV)
        self.assertEqual(batch.source_ref, "timetable.csv")

    def test_file_preview_rejects_unsupported_extension(self):
        uploaded = SimpleUploadedFile(
            "timetable.xlsx",
            b"not really xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        resp = self.client.post(
            "/api/imports/file/preview",
            {"file": uploaded, "target_date": "2026-03-10"},
        )

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "invalid_excel_file")

    def test_excel_preview_returns_valid_sessions(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Week 3"
        sheet.append(["Day", "Start Time", "End Time", "Subject", "Topic", "Group"])
        sheet.append(["Tuesday", "09:40", "10:30", "Physiology", "ANS I", "Whole class"])
        sheet.append(["Tuesday", "10:40", "11:30", "Embryology", "Somites", "Group A"])
        stream = io.BytesIO()
        workbook.save(stream)

        uploaded = SimpleUploadedFile(
            "timetable.xlsx",
            stream.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        resp = self.client.post(
            "/api/imports/file/preview",
            {
                "file": uploaded,
                "target_date": "2026-03-10",
                "default_course_map_id": str(self.course.id),
            },
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["selected_sheet"], "Week 3")
        self.assertEqual(data["summary"]["valid_sessions"], 2)

    def test_file_preview_returns_clear_missing_column_error(self):
        uploaded = SimpleUploadedFile(
            "bad-template.csv",
            (
                "Faculty,Room,Notes\n"
                "Dr Smith,Hall A,No usable timetable columns\n"
            ).encode("utf-8"),
            content_type="text/csv",
        )

        resp = self.client.post(
            "/api/imports/file/preview",
            {
                "file": uploaded,
                "target_date": "2026-03-10",
                "default_course_map_id": str(self.course.id),
            },
        )

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "missing_required_columns")
        self.assertIn("Day or Date", resp.json()["detail"])


# ---------------------------------------------------------------------------
# Unit tests — SessionDisplayTitleBuilder
# ---------------------------------------------------------------------------

class TitleBuilderTests(TestCase):
    def test_direct_title_used_as_is(self):
        class FakeSession:
            title = "Anatomy-A,B,C"
            subject = "Anatomy"
            group = "A,B,C"

        self.assertEqual(SessionDisplayTitleBuilder.build(FakeSession()), "Anatomy-A,B,C")

    def test_compose_subject_and_group(self):
        self.assertEqual(SessionDisplayTitleBuilder.compose("Anatomy", "A,B,C"), "Anatomy-A,B,C")

    def test_compose_subject_and_session_type(self):
        self.assertEqual(
            SessionDisplayTitleBuilder.compose("Embryology", session_type="Lecture"),
            "Embryology Lecture",
        )

    def test_compose_subject_only(self):
        self.assertEqual(SessionDisplayTitleBuilder.compose("Physiology"), "Physiology")

    def test_fallback_to_compose_when_title_empty(self):
        class FakeSession:
            title = ""
            subject = "Biochemistry"
            group = "D"

        self.assertEqual(SessionDisplayTitleBuilder.build(FakeSession()), "Biochemistry-D")


# ---------------------------------------------------------------------------
# Unit tests — time / date formatters
# ---------------------------------------------------------------------------

class TimeFormatterTests(TestCase):
    def test_same_period_am(self):
        self.assertEqual(format_time_range(time(8, 0), time(9, 30)), "8:00 \u2013 9:30am")

    def test_same_period_pm(self):
        self.assertEqual(format_time_range(time(13, 0), time(14, 30)), "1:00 \u2013 2:30pm")

    def test_cross_noon(self):
        self.assertEqual(format_time_range(time(11, 15), time(13, 15)), "11:15am \u2013 1:15pm")

    def test_str_input(self):
        self.assertEqual(format_time_range("09:30", "10:30"), "9:30 \u2013 10:30am")


class DateFormatterTests(TestCase):
    def test_no_year(self):
        self.assertEqual(format_date(date(2026, 3, 10)), "Tuesday, March 10")

    def test_with_year(self):
        self.assertEqual(format_date(date(2026, 3, 10), include_year=True), "Tuesday, March 10, 2026")

    def test_str_input(self):
        self.assertEqual(format_date("2026-03-10"), "Tuesday, March 10")


# ---------------------------------------------------------------------------
# Unit tests — CombinedDayMessageRenderer
# ---------------------------------------------------------------------------

class CombinedDayMessageRendererTests(TestCase):
    def _make_session(self, *, sid, title, start, end, meet_link=""):
        class FakeMeetEvent:
            pass

        class FakeSession:
            pass

        s = FakeSession()
        s.id = sid
        s.title = title
        s.subject = ""
        s.group = ""
        s.date = date(2026, 3, 10)
        s.start_time = time(*[int(x) for x in start.split(":")])
        s.end_time = time(*[int(x) for x in end.split(":")])
        if meet_link:
            evt = FakeMeetEvent()
            evt.meet_link = meet_link
            s.meet_event = evt
        else:
            s.meet_event = None
        return s

    def _five_sessions(self):
        return [
            self._make_session(sid=1, title="Anatomy-A,B,C", start="08:00", end="09:30",
                               meet_link="https://meet.google.com/ots-gfuz-eyg"),
            self._make_session(sid=2, title="Biochemistry-D", start="08:00", end="09:30",
                               meet_link="https://meet.google.com/emj-nfss-hkx"),
            self._make_session(sid=3, title="Histo-F", start="08:00", end="09:30",
                               meet_link="https://meet.google.com/ejd-khbn-svw"),
            self._make_session(sid=4, title="Physiology-E", start="08:00", end="09:30",
                               meet_link="https://meet.google.com/duj-sqat-bbc"),
            self._make_session(sid=5, title="Embryology Lecture", start="09:30", end="10:30",
                               meet_link="https://meet.google.com/pwx-mwtt-pbp"),
        ]

    def test_exact_output_matches_spec(self):
        renderer = CombinedDayMessageRenderer()
        result = renderer.render(self._five_sessions())
        expected = (
            "Anatomy-A,B,C\n"
            "Tuesday, March 10 \u00b7 8:00 \u2013 9:30am\n"
            "Video call link: https://meet.google.com/ots-gfuz-eyg\n\n"
            "Biochemistry-D\n"
            "Tuesday, March 10 \u00b7 8:00 \u2013 9:30am\n"
            "Video call link: https://meet.google.com/emj-nfss-hkx\n\n"
            "Histo-F\n"
            "Tuesday, March 10 \u00b7 8:00 \u2013 9:30am\n"
            "Video call link: https://meet.google.com/ejd-khbn-svw\n\n"
            "Physiology-E\n"
            "Tuesday, March 10 \u00b7 8:00 \u2013 9:30am\n"
            "Video call link: https://meet.google.com/duj-sqat-bbc\n\n"
            "Embryology Lecture\n"
            "Tuesday, March 10 \u00b7 9:30 \u2013 10:30am\n"
            "Video call link: https://meet.google.com/pwx-mwtt-pbp"
        )
        self.assertEqual(result["message"], expected)
        self.assertEqual(result["session_count"], 5)

    def test_no_trailing_blank_line(self):
        renderer = CombinedDayMessageRenderer()
        result = renderer.render(self._five_sessions())
        self.assertFalse(result["message"].endswith("\n"))

    def test_exactly_one_blank_line_between_blocks(self):
        renderer = CombinedDayMessageRenderer()
        result = renderer.render(self._five_sessions())
        self.assertNotIn("\n\n\n", result["message"])

    def test_sort_by_time(self):
        sessions = list(reversed(self._five_sessions()))
        renderer = CombinedDayMessageRenderer()
        result = renderer.render(sessions, {"sort_by_time": True})
        lines = result["message"].splitlines()
        self.assertEqual(lines[0], "Anatomy-A,B,C")

    def test_duplicate_skipped(self):
        sessions = self._five_sessions()
        # add exact duplicate of first session
        dup = self._make_session(sid=99, title="Anatomy-A,B,C", start="08:00", end="09:30",
                                 meet_link="https://meet.google.com/ots-gfuz-eyg")
        sessions.append(dup)
        renderer = CombinedDayMessageRenderer()
        result = renderer.render(sessions)
        self.assertEqual(result["session_count"], 5)
        self.assertEqual(result["skipped_count"], 1)
        self.assertEqual(result["skipped"][0]["reason"], "duplicate")

    def test_missing_title_skipped(self):
        sessions = self._five_sessions()
        no_title = self._make_session(sid=10, title="", start="10:00", end="11:00")
        sessions.append(no_title)
        renderer = CombinedDayMessageRenderer()
        result = renderer.render(sessions)
        self.assertEqual(result["session_count"], 5)
        self.assertEqual(result["skipped_count"], 1)

    def test_missing_meet_link_warning(self):
        sessions = self._five_sessions()
        no_link = self._make_session(sid=11, title="No Link Session", start="11:00", end="12:00")
        sessions.append(no_link)
        renderer = CombinedDayMessageRenderer()
        result = renderer.render(sessions)
        self.assertEqual(len(result["warnings"]), 1)
        self.assertIn("missing meet link", result["warnings"][0]["warning"])

    def test_include_year_option(self):
        renderer = CombinedDayMessageRenderer()
        result = renderer.render(
            self._five_sessions()[:1], {"include_year": True}
        )
        self.assertIn("2026", result["message"])

    def test_include_day_heading(self):
        renderer = CombinedDayMessageRenderer()
        result = renderer.render(
            self._five_sessions()[:1], {"include_day_heading": True}
        )
        self.assertTrue(result["message"].startswith("Tuesday timetable"))

    def test_no_video_label_option(self):
        renderer = CombinedDayMessageRenderer()
        result = renderer.render(
            self._five_sessions()[:1], {"include_video_label": False}
        )
        self.assertNotIn("Video call link:", result["message"])


# ---------------------------------------------------------------------------
# Integration tests — combined-day API endpoints
# ---------------------------------------------------------------------------

class CombinedDayEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(email="publish@example.com", password="pass123")
        self.course = Course.objects.create(
            user=self.user, google_course_id="c-pub-001", name="Year 1"
        )
        self.sessions = []
        meet_links = [
            "https://meet.google.com/ots-gfuz-eyg",
            "https://meet.google.com/emj-nfss-hkx",
            "https://meet.google.com/ejd-khbn-svw",
        ]
        titles = ["Anatomy-A,B,C", "Biochemistry-D", "Histo-F"]
        for i, (t, ml) in enumerate(zip(titles, meet_links)):
            s = Session.objects.create(
                course=self.course,
                date=date(2026, 3, 10),
                start_time=time(8, 0),
                end_time=time(9, 30),
                title=t,
            )
            MeetEvent.objects.create(session=s, calendar_event_id=f"evt-{i}", meet_link=ml)
            self.sessions.append(s)
        self.client.force_authenticate(self.user)

    def test_preview_returns_combined_message(self):
        resp = self.client.post(
            "/api/publish/combined-day-preview",
            {
                "session_ids": [s.id for s in self.sessions],
                "template": "single_day_combined_message",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["template"], "single_day_combined_message")
        self.assertEqual(data["session_count"], 3)
        self.assertIn("Anatomy-A,B,C", data["message"])
        self.assertIn("Video call link:", data["message"])
        self.assertIn("Tuesday, March 10", data["message"])

    def test_preview_with_options(self):
        resp = self.client.post(
            "/api/publish/combined-day-preview",
            {
                "session_ids": [s.id for s in self.sessions],
                "template": "single_day_combined_message",
                "options": {"include_year": True, "include_day_heading": True},
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("2026", data["message"])
        self.assertTrue(data["message"].startswith("Tuesday timetable"))

    def test_preview_empty_session_ids_returns_400(self):
        resp = self.client.post(
            "/api/publish/combined-day-preview",
            {"session_ids": [], "template": "single_day_combined_message"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_preview_unsupported_template_returns_400(self):
        resp = self.client.post(
            "/api/publish/combined-day-preview",
            {"session_ids": [self.sessions[0].id], "template": "separate_posts"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_preview_only_sees_own_sessions(self):
        other_user = get_user_model().objects.create_user(
            email="other2@example.com", password="pass"
        )
        other_course = Course.objects.create(
            user=other_user, google_course_id="c-other-2", name="Other"
        )
        other_session = Session.objects.create(
            course=other_course,
            date=date(2026, 3, 10),
            start_time=time(8, 0),
            end_time=time(9, 30),
            title="Hidden Session",
        )
        resp = self.client.post(
            "/api/publish/combined-day-preview",
            {
                "session_ids": [s.id for s in self.sessions] + [other_session.id],
                "template": "single_day_combined_message",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["session_count"], 3)
        self.assertNotIn("Hidden Session", resp.json()["message"])

    @patch("core.views.GoogleService.create_classroom_announcement")
    def test_publish_posts_announcement(self, mock_announce):
        mock_announce.return_value = "announce-001"
        resp = self.client.post(
            "/api/publish/combined-day-post",
            {
                "session_ids": [s.id for s in self.sessions],
                "course_id": "c-pub-001",
                "template": "single_day_combined_message",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data["google_post_id"], "announce-001")
        self.assertEqual(data["posting_mode"], "single_day_combined_message")
        self.assertEqual(data["session_count"], 3)
        mock_announce.assert_called_once()
        call_text = mock_announce.call_args[0][1]
        self.assertIn("Anatomy-A,B,C", call_text)

    def test_publish_missing_course_id_returns_400(self):
        resp = self.client.post(
            "/api/publish/combined-day-post",
            {
                "session_ids": [s.id for s in self.sessions],
                "template": "single_day_combined_message",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

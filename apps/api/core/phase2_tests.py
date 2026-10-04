"""Phase 2 tests — Admin Commands + Enrollment.

Unit tests for:
- Model creation
- Permission enforcement
- Bundle management
- Command executor preview + job building
- CSV parsing
- Group-to-course expansion logic
- Duplicate protection
- API endpoint responses (mocked Google calls)

Integration tests for:
- Create CommandJob
- Create CommandJobItem records
- Execute add student to course (mocked API)
- Execute add teacher to course (mocked API)
- Execute add member to group (mocked API)
- Enroll group to course (mocked API)
- CSV import preview and run flow
- Retry failed items
"""

from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import (
    ActionType,
    CommandJob,
    CommandJobItem,
    DirectoryTarget,
    ItemStatus,
    JobStatus,
    OnboardingBundle,
    RoleType,
    TargetType,
)
from .google_scopes import SCOPE_CLASSROOM_ROSTERS
from .services.command_executor import CommandExecutor, CommandExecutorError
from .services.classroom_service import ClassroomRosterService, ClassroomServiceError
from .services.google_directory_service import GoogleDirectoryService, DirectoryServiceError

User = get_user_model()


def make_user(email="admin@school.edu", is_staff=True) -> User:
    return User.objects.create_user(email=email, password="testpass123", is_staff=is_staff)


# ===========================================================================
# Model tests
# ===========================================================================

class DirectoryTargetModelTests(TestCase):
    def test_create_group_target(self):
        t = DirectoryTarget.objects.create(
            target_type=TargetType.GROUP,
            external_id="g001",
            email="science@school.edu",
            display_name="Science Group",
        )
        self.assertEqual(str(t), "group:science@school.edu")

    def test_unique_together_enforced(self):
        DirectoryTarget.objects.create(target_type=TargetType.GROUP, external_id="g001")
        with self.assertRaises(Exception):
            DirectoryTarget.objects.create(target_type=TargetType.GROUP, external_id="g001")


class OnboardingBundleModelTests(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_create_bundle(self):
        b = OnboardingBundle.objects.create(
            name="Year 1 Student Bundle",
            role_type=RoleType.STUDENT,
            groups_json=["year1@school.edu"],
            classroom_courses_json=["c001", "c002"],
            created_by=self.user,
        )
        self.assertEqual(str(b), "Year 1 Student Bundle")
        self.assertTrue(b.active)

    def test_bundle_defaults(self):
        b = OnboardingBundle.objects.create(name="Test Bundle")
        self.assertEqual(b.role_type, "student")
        self.assertEqual(b.groups_json, [])
        self.assertTrue(b.active)


class CommandJobModelTests(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_create_job(self):
        job = CommandJob.objects.create(
            job_type=ActionType.ADD_STUDENT_TO_COURSE,
            created_by=self.user,
            target_summary_json={"course_id": "c001", "student_email": "s@school.edu"},
        )
        self.assertEqual(job.status, JobStatus.PENDING)
        self.assertFalse(job.dry_run)

    def test_job_item_creation(self):
        job = CommandJob.objects.create(
            job_type=ActionType.ADD_USER_TO_GROUP,
            created_by=self.user,
        )
        item = CommandJobItem.objects.create(
            command_job=job,
            target_type=TargetType.GROUP,
            target_ref="group@school.edu",
            action=ActionType.ADD_USER_TO_GROUP,
            payload_json={"group_email": "group@school.edu", "user_email": "u@school.edu"},
        )
        self.assertEqual(item.status, ItemStatus.PENDING)
        self.assertEqual(item.retry_count, 0)
        self.assertEqual(job.items.count(), 1)


# ===========================================================================
# Permission tests
# ===========================================================================

class AdminPermissionTests(TestCase):
    def setUp(self):
        self.admin = make_user("admin@school.edu", is_staff=True)
        self.regular = make_user("user@school.edu", is_staff=False)
        self.client = APIClient()

    def test_regular_user_cannot_access_groups(self):
        self.client.force_authenticate(self.regular)
        resp = self.client.get("/api/groups")
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_access_groups(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get("/api/groups")
        self.assertEqual(resp.status_code, 200)

    def test_regular_user_cannot_list_bundles(self):
        self.client.force_authenticate(self.regular)
        resp = self.client.get("/api/bundles")
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_list_bundles(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get("/api/bundles")
        self.assertEqual(resp.status_code, 200)

    def test_unauthenticated_cannot_access_commands(self):
        resp = self.client.post("/api/commands/run", {"command_type": "ADD_USER_TO_GROUP"}, format="json")
        self.assertIn(resp.status_code, [401, 403])


# ===========================================================================
# Bundle API tests
# ===========================================================================

class BundleAPITests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_create_bundle(self):
        resp = self.client.post("/api/bundles/create", {
            "name": "Freshers",
            "role_type": "student",
            "groups_json": ["freshers@school.edu"],
            "classroom_courses_json": ["c123"],
            "active": True,
        }, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["name"], "Freshers")

    def test_update_bundle(self):
        b = OnboardingBundle.objects.create(name="Old Name", created_by=self.user)
        resp = self.client.patch(f"/api/bundles/{b.id}", {"name": "New Name"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["name"], "New Name")

    def test_delete_bundle(self):
        b = OnboardingBundle.objects.create(name="To Delete", created_by=self.user)
        resp = self.client.delete(f"/api/bundles/{b.id}/delete")
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(OnboardingBundle.objects.filter(id=b.id).exists())

    def test_list_bundles(self):
        OnboardingBundle.objects.create(name="B1", created_by=self.user)
        OnboardingBundle.objects.create(name="B2", created_by=self.user)
        resp = self.client.get("/api/bundles")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 2)

    def test_bundle_requires_name(self):
        resp = self.client.post("/api/bundles/create", {"role_type": "student"}, format="json")
        self.assertEqual(resp.status_code, 400)


# ===========================================================================
# Command executor unit tests
# ===========================================================================

class CommandExecutorCSVTests(TestCase):
    def setUp(self):
        self.user = make_user()

    def _make_executor(self):
        with patch("core.services.command_executor.GoogleDirectoryService"), \
             patch("core.services.command_executor.ClassroomRosterService"):
            executor = CommandExecutor.__new__(CommandExecutor)
            executor.user = self.user
            executor._dir_service = MagicMock()
            executor._class_service = MagicMock()
            return executor

    def test_csv_preview_valid_rows(self):
        executor = self._make_executor()
        csv = "email,name,role\nstudent1@school.edu,Alice,student\nstudent2@school.edu,Bob,student"
        result = executor.preview_csv(csv)
        self.assertEqual(result["valid_rows"], 2)
        self.assertEqual(result["error_rows"], 0)
        self.assertEqual(result["rows"][0]["email"], "student1@school.edu")

    def test_csv_preview_missing_email_reported_as_error(self):
        executor = self._make_executor()
        csv = "email,name\n,Alice\nbob@school.edu,Bob"
        result = executor.preview_csv(csv)
        self.assertEqual(result["error_rows"], 1)
        self.assertEqual(result["valid_rows"], 1)

    def test_csv_preview_no_headers_raises(self):
        executor = self._make_executor()
        with self.assertRaises(CommandExecutorError):
            executor.preview_csv("")

    def test_csv_preview_extra_groups_parsed(self):
        executor = self._make_executor()
        csv = "email,extra_groups\nstudent@school.edu,g1@s.edu,g2@s.edu"
        result = executor.preview_csv(csv)
        # Should succeed even if groups parsing treats extra cols as data
        self.assertGreaterEqual(result["total_rows"], 1)

    def test_csv_preview_with_bundle_name(self):
        executor = self._make_executor()
        csv = "email,bundle\nstudent@school.edu,Year1Bundle"
        result = executor.preview_csv(csv)
        self.assertEqual(result["rows"][0]["bundle"], "Year1Bundle")


class CommandExecutorPreviewTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self._dir_mock = MagicMock()
        self._class_mock = MagicMock()

    def _executor(self):
        executor = CommandExecutor.__new__(CommandExecutor)
        executor.user = self.user
        executor._dir_service = self._dir_mock
        executor._class_service = self._class_mock
        return executor

    def test_preview_add_user_to_group_not_member(self):
        self._dir_mock.is_member_of_group.return_value = False
        ex = self._executor()
        result = ex.preview_add_user_to_group("g@school.edu", "u@school.edu")
        self.assertFalse(result["would_skip"])

    def test_preview_add_user_to_group_already_member(self):
        self._dir_mock.is_member_of_group.return_value = True
        ex = self._executor()
        result = ex.preview_add_user_to_group("g@school.edu", "u@school.edu")
        self.assertTrue(result["would_skip"])
        self.assertEqual(result["skip_reason"], "already_member")

    def test_preview_add_student_not_enrolled(self):
        self._class_mock.list_students.return_value = []
        ex = self._executor()
        result = ex.preview_add_student_to_course("c001", "s@school.edu")
        self.assertFalse(result["would_skip"])

    def test_preview_add_student_already_enrolled(self):
        self._class_mock.list_students.return_value = ["s@school.edu"]
        ex = self._executor()
        result = ex.preview_add_student_to_course("c001", "s@school.edu")
        self.assertTrue(result["would_skip"])
        self.assertEqual(result["skip_reason"], "already_enrolled")

    def test_preview_enroll_group_to_course_expansion(self):
        self._dir_mock.list_group_members.return_value = [
            {"email": "u1@s.edu", "type": "USER"},
            {"email": "u2@s.edu", "type": "USER"},
        ]
        self._class_mock.list_students.return_value = ["u1@s.edu"]
        ex = self._executor()
        result = ex.preview_enroll_group_to_course("g@s.edu", "c001")
        self.assertEqual(result["total_members"], 2)
        self.assertEqual(result["enroll_count"], 1)
        self.assertEqual(result["skip_count"], 1)
        self.assertIn("u2@s.edu", result["to_enroll"])
        self.assertIn("u1@s.edu", result["to_skip"])


class CommandExecutorJobBuildTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self._dir_mock = MagicMock()
        self._class_mock = MagicMock()

    def _executor(self):
        executor = CommandExecutor.__new__(CommandExecutor)
        executor.user = self.user
        executor._dir_service = self._dir_mock
        executor._class_service = self._class_mock
        return executor

    def test_build_add_user_to_group_job_creates_one_item(self):
        ex = self._executor()
        job = ex.build_add_user_to_group_job("g@s.edu", "u@s.edu")
        self.assertEqual(job.job_type, ActionType.ADD_USER_TO_GROUP)
        self.assertEqual(job.items.count(), 1)
        item = job.items.first()
        self.assertEqual(item.action, ActionType.ADD_USER_TO_GROUP)

    def test_build_enroll_group_to_course_creates_per_user_items(self):
        self._dir_mock.list_group_members.return_value = [
            {"email": "u1@s.edu", "type": "USER"},
            {"email": "u2@s.edu", "type": "USER"},
            {"email": "u3@s.edu", "type": "USER"},
        ]
        ex = self._executor()
        job = ex.build_enroll_group_to_course_job("g@s.edu", "c001")
        self.assertEqual(job.items.count(), 3)
        self.assertTrue(all(i.action == ActionType.ADD_STUDENT_TO_COURSE for i in job.items.all()))

    def test_build_enroll_group_teacher_role_creates_add_teacher_items(self):
        self._dir_mock.list_group_members.return_value = [
            {"email": "t1@s.edu", "type": "USER"},
        ]
        ex = self._executor()
        job = ex.build_enroll_group_to_course_job("g@s.edu", "c001", role="teacher")
        self.assertEqual(job.items.first().action, ActionType.ADD_TEACHER_TO_COURSE)

    def test_build_apply_bundle_job_creates_correct_items(self):
        bundle = OnboardingBundle.objects.create(
            name="Bundle",
            role_type=RoleType.STUDENT,
            groups_json=["g1@s.edu", "g2@s.edu"],
            classroom_courses_json=["c001"],
            created_by=self.user,
        )
        ex = self._executor()
        job = ex.build_apply_bundle_job("u@s.edu", bundle.id)
        # 2 group items + 1 course item
        self.assertEqual(job.items.count(), 3)
        group_items = job.items.filter(action=ActionType.ADD_USER_TO_GROUP)
        course_items = job.items.filter(action=ActionType.ADD_STUDENT_TO_COURSE)
        self.assertEqual(group_items.count(), 2)
        self.assertEqual(course_items.count(), 1)

    def test_build_apply_bundle_inactive_raises(self):
        bundle = OnboardingBundle.objects.create(name="Inactive", active=False)
        ex = self._executor()
        with self.assertRaises(CommandExecutorError):
            ex.build_apply_bundle_job("u@s.edu", bundle.id)

    def test_dry_run_job_has_dry_run_flag(self):
        ex = self._executor()
        job = ex.build_add_user_to_group_job("g@s.edu", "u@s.edu", dry_run=True)
        self.assertTrue(job.dry_run)
        self.assertEqual(job.status, JobStatus.DRY_RUN)


# ===========================================================================
# Command execution integration tests
# ===========================================================================

class CommandExecutorExecuteTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self._dir_mock = MagicMock()
        self._class_mock = MagicMock()

    def _executor(self):
        executor = CommandExecutor.__new__(CommandExecutor)
        executor.user = self.user
        executor._dir_service = self._dir_mock
        executor._class_service = self._class_mock
        return executor

    def _make_job_with_item(self, action: str, payload: dict) -> tuple[CommandJob, CommandJobItem]:
        job = CommandJob.objects.create(job_type=action, created_by=self.user)
        item = CommandJobItem.objects.create(
            command_job=job,
            target_type=TargetType.USER,
            target_ref=payload.get("user_email", "u@s.edu"),
            action=action,
            payload_json=payload,
        )
        return job, item

    def test_execute_add_student_to_course_success(self):
        self._class_mock.add_student_to_course.return_value = {"success": True}
        job, _ = self._make_job_with_item(
            ActionType.ADD_STUDENT_TO_COURSE,
            {"course_id": "c001", "user_email": "s@s.edu"},
        )
        ex = self._executor()
        summary = ex.execute_job(job)
        self.assertEqual(summary["success"], 1)
        self.assertEqual(summary["failed"], 0)
        job.refresh_from_db()
        self.assertEqual(job.status, JobStatus.COMPLETED)

    def test_execute_add_teacher_to_course_success(self):
        self._class_mock.add_teacher_to_course.return_value = {"success": True}
        job, _ = self._make_job_with_item(
            ActionType.ADD_TEACHER_TO_COURSE,
            {"course_id": "c001", "user_email": "t@s.edu"},
        )
        ex = self._executor()
        summary = ex.execute_job(job)
        self.assertEqual(summary["success"], 1)

    def test_execute_add_member_to_group_success(self):
        self._dir_mock.add_member_to_group.return_value = {"success": True}
        job, _ = self._make_job_with_item(
            ActionType.ADD_USER_TO_GROUP,
            {"group_email": "g@s.edu", "user_email": "u@s.edu"},
        )
        ex = self._executor()
        summary = ex.execute_job(job)
        self.assertEqual(summary["success"], 1)

    def test_execute_skipped_item_not_counted_as_success(self):
        self._class_mock.add_student_to_course.return_value = {"skipped": True, "reason": "already_enrolled"}
        job, _ = self._make_job_with_item(
            ActionType.ADD_STUDENT_TO_COURSE,
            {"course_id": "c001", "user_email": "s@s.edu"},
        )
        ex = self._executor()
        summary = ex.execute_job(job)
        self.assertEqual(summary["skipped"], 1)
        self.assertEqual(summary["success"], 0)

    def test_execute_failed_item_updates_job_status(self):
        self._class_mock.add_student_to_course.side_effect = ClassroomServiceError("API error")
        job, _ = self._make_job_with_item(
            ActionType.ADD_STUDENT_TO_COURSE,
            {"course_id": "c001", "user_email": "s@s.edu"},
        )
        ex = self._executor()
        summary = ex.execute_job(job)
        self.assertEqual(summary["failed"], 1)
        job.refresh_from_db()
        self.assertEqual(job.status, JobStatus.FAILED)

    def test_execute_mixed_partial_status(self):
        # first succeeds, second fails
        self._class_mock.add_student_to_course.side_effect = [
            {"success": True},
            ClassroomServiceError("quota"),
        ]
        job = CommandJob.objects.create(job_type=ActionType.ADD_STUDENT_TO_COURSE, created_by=self.user)
        CommandJobItem.objects.create(
            command_job=job, target_type=TargetType.USER, target_ref="s1@s.edu",
            action=ActionType.ADD_STUDENT_TO_COURSE,
            payload_json={"course_id": "c001", "user_email": "s1@s.edu"},
        )
        CommandJobItem.objects.create(
            command_job=job, target_type=TargetType.USER, target_ref="s2@s.edu",
            action=ActionType.ADD_STUDENT_TO_COURSE,
            payload_json={"course_id": "c001", "user_email": "s2@s.edu"},
        )
        ex = self._executor()
        summary = ex.execute_job(job)
        self.assertEqual(summary["success"], 1)
        self.assertEqual(summary["failed"], 1)
        job.refresh_from_db()
        self.assertEqual(job.status, JobStatus.PARTIAL)

    def test_dry_run_does_not_call_google_apis(self):
        job = CommandJob.objects.create(
            job_type=ActionType.ADD_STUDENT_TO_COURSE, created_by=self.user, dry_run=True,
            status=JobStatus.DRY_RUN,
        )
        ex = self._executor()
        summary = ex.execute_job(job)
        self.assertIn("dry_run", summary.get("message", ""))
        self._class_mock.add_student_to_course.assert_not_called()

    def test_retry_only_reruns_failed_items(self):
        self._class_mock.add_student_to_course.return_value = {"success": True}
        job = CommandJob.objects.create(job_type=ActionType.ADD_STUDENT_TO_COURSE, created_by=self.user)
        # One succeeded, one failed
        CommandJobItem.objects.create(
            command_job=job, target_type=TargetType.USER, target_ref="s1@s.edu",
            action=ActionType.ADD_STUDENT_TO_COURSE,
            payload_json={"course_id": "c001", "user_email": "s1@s.edu"},
            status=ItemStatus.SUCCESS,
        )
        CommandJobItem.objects.create(
            command_job=job, target_type=TargetType.USER, target_ref="s2@s.edu",
            action=ActionType.ADD_STUDENT_TO_COURSE,
            payload_json={"course_id": "c001", "user_email": "s2@s.edu"},
            status=ItemStatus.FAILED,
        )
        ex = self._executor()
        ex.retry_failed_items(job)
        # Only 1 call to Google (the failed item)
        self._class_mock.add_student_to_course.assert_called_once()


# ===========================================================================
# CSV Import API tests
# ===========================================================================

class CsvImportAPITests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_csv_preview_endpoint_returns_preview(self):
        csv_data = "email,name,role\nstudent@school.edu,Alice,student"
        resp = self.client.post("/api/commands/import/csv/preview", {"csv_text": csv_data}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("valid_rows", resp.data)
        self.assertEqual(resp.data["valid_rows"], 1)

    def test_csv_preview_empty_returns_400(self):
        resp = self.client.post("/api/commands/import/csv/preview", {"csv_text": ""}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_csv_preview_missing_email_column_reported(self):
        csv_data = "email,name\n,Alice"
        resp = self.client.post("/api/commands/import/csv/preview", {"csv_text": csv_data}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["error_rows"], 1)

    @patch("core.admin_views.execute_command_job_task.delay")
    def test_csv_run_creates_job(self, mock_delay):
        csv_data = "email,name,role\nstudent@school.edu,Alice,student"
        resp = self.client.post("/api/commands/import/csv/run", {"csv_text": csv_data}, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertIn("id", resp.data)
        mock_delay.assert_called_once()


# ===========================================================================
# Commands API endpoint tests
# ===========================================================================

class CommandsAPITests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    @patch("core.admin_views.execute_command_job_task.delay")
    def test_run_add_student_creates_job(self, mock_delay):
        resp = self.client.post("/api/commands/run", {
            "command_type": "ADD_STUDENT_TO_COURSE",
            "params": {"course_id": "c001", "student_email": "s@s.edu"},
        }, format="json")
        self.assertEqual(resp.status_code, 201)
        mock_delay.assert_called_once()

    @patch("core.admin_views.execute_command_job_task.delay")
    def test_run_add_teacher_creates_job(self, mock_delay):
        resp = self.client.post("/api/commands/run", {
            "command_type": "ADD_TEACHER_TO_COURSE",
            "params": {"course_id": "c001", "teacher_email": "t@s.edu"},
        }, format="json")
        self.assertEqual(resp.status_code, 201)

    def test_run_unknown_command_type_returns_400(self):
        resp = self.client.post("/api/commands/run", {"command_type": "NOOP"}, format="json")
        self.assertEqual(resp.status_code, 400)

    @patch("core.admin_views.CommandExecutor.preview_remove_student")
    def test_preview_remove_student_command(self, mock_preview):
        mock_preview.return_value = {"allowed": True, "action": "REMOVE_STUDENT_FROM_COURSE"}
        resp = self.client.post(
            "/api/commands/preview",
            {
                "command_type": "REMOVE_STUDENT_FROM_COURSE",
                "params": {"course_id": "c001", "student_email": "s@s.edu"},
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["allowed"])

    @patch("core.admin_views.CommandExecutor.preview_remove_teacher")
    def test_preview_remove_teacher_command(self, mock_preview):
        mock_preview.return_value = {"allowed": True, "action": "REMOVE_TEACHER_FROM_COURSE"}
        resp = self.client.post(
            "/api/commands/preview",
            {
                "command_type": "REMOVE_TEACHER_FROM_COURSE",
                "params": {"course_id": "c001", "teacher_email": "t@s.edu"},
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["allowed"])

    @patch("core.admin_views.execute_command_job_task.delay")
    def test_run_remove_student_creates_job(self, mock_delay):
        resp = self.client.post(
            "/api/commands/run",
            {
                "command_type": "REMOVE_STUDENT_FROM_COURSE",
                "params": {"course_id": "c001", "student_email": "s@s.edu"},
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        mock_delay.assert_called_once()

    @patch("core.admin_views.execute_command_job_task.delay")
    def test_run_remove_teacher_creates_job(self, mock_delay):
        resp = self.client.post(
            "/api/commands/run",
            {
                "command_type": "REMOVE_TEACHER_FROM_COURSE",
                "params": {"course_id": "c001", "teacher_email": "t@s.edu"},
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        mock_delay.assert_called_once()

    def test_list_jobs_empty(self):
        resp = self.client.get("/api/commands/jobs")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 0)

    def test_get_job_not_found(self):
        resp = self.client.get("/api/commands/jobs/9999")
        self.assertEqual(resp.status_code, 404)

    def test_list_jobs_shows_own_jobs(self):
        CommandJob.objects.create(job_type=ActionType.ADD_USER_TO_GROUP, created_by=self.user)
        other_user = make_user("other@s.edu", is_staff=True)
        CommandJob.objects.create(job_type=ActionType.ADD_USER_TO_GROUP, created_by=other_user)
        resp = self.client.get("/api/commands/jobs")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)  # Only own jobs

    def test_get_job_with_items(self):
        job = CommandJob.objects.create(job_type=ActionType.ADD_USER_TO_GROUP, created_by=self.user)
        CommandJobItem.objects.create(
            command_job=job, target_type=TargetType.GROUP, target_ref="g@s.edu",
            action=ActionType.ADD_USER_TO_GROUP, payload_json={},
        )
        resp = self.client.get(f"/api/commands/jobs/{job.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data["items"]), 1)

    @patch("core.admin_views.retry_command_job_task.delay")
    def test_retry_job(self, mock_delay):
        job = CommandJob.objects.create(job_type=ActionType.ADD_USER_TO_GROUP, created_by=self.user)
        resp = self.client.post("/api/commands/retry", {"job_id": job.id}, format="json")
        self.assertEqual(resp.status_code, 200)
        mock_delay.assert_called_once_with(job.id)


class ScopeGuardApiTests(TestCase):
    def setUp(self):
        self.user = make_user(email="scope-admin@school.edu", is_staff=False)
        self.user.role = "admin"
        self.user.google_scopes = ""
        self.user.google_scopes_json = []
        self.user.save(update_fields=["role", "google_scopes", "google_scopes_json"])
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    @patch("core.services.classroom_service.GoogleService.classroom")
    def test_add_student_requires_roster_scope_before_google_call(self, classroom_mock):
        resp = self.client.post(
            "/api/classroom/add-student",
            {"course_id": "c001", "student_email": "s@s.edu"},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)
        payload = resp.json()
        self.assertEqual(payload.get("code"), "GOOGLE_SCOPE_MISSING")
        self.assertEqual(payload.get("feature"), "bulk_add_students")
        self.assertIn(SCOPE_CLASSROOM_ROSTERS, payload.get("missingScopes", []))
        classroom_mock.assert_not_called()


# ===========================================================================
# Phase 2B — Classroom Lifecycle + Direct Removal Tests
# ===========================================================================

from unittest.mock import MagicMock, patch, PropertyMock
from core.services.classroom_service import ClassroomRosterService, ClassroomServiceError


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _classroom_svc(user):
    svc = ClassroomRosterService(user)
    svc._google = MagicMock()
    return svc


def _make_http_error(status_code: int):
    from googleapiclient.errors import HttpError
    import json
    resp = MagicMock()
    resp.status = status_code
    content = json.dumps({"error": {"code": status_code, "message": "error"}}).encode()
    return HttpError(resp=resp, content=content)


class Phase2TestBase(TestCase):
    """Shared base for Phase 2B tests — sets up admin and regular_user."""
    def setUp(self):
        self.admin = make_user("admin2b@school.edu", is_staff=True)
        self.regular_user = make_user("reg2b@school.edu", is_staff=False)
        self.client = APIClient()
        self.client.force_authenticate(self.admin)


# ---------------------------------------------------------------------------
# get_course
# ---------------------------------------------------------------------------

class GetCourseTests(Phase2TestBase):

    @patch("core.services.classroom_service.GoogleService")
    def test_get_course_success(self, MockGS):
        svc = _classroom_svc(self.admin)
        svc._google.classroom.return_value.courses.return_value.get.return_value.execute.return_value = {
            "id": "c1", "name": "Test", "courseState": "ACTIVE"
        }
        result = svc.get_course("c1")
        self.assertEqual(result["id"], "c1")

    @patch("core.services.classroom_service.GoogleService")
    def test_get_course_not_found(self, MockGS):
        svc = _classroom_svc(self.admin)
        svc._google.classroom.return_value.courses.return_value.get.return_value.execute.side_effect = _make_http_error(404)
        with self.assertRaises(ClassroomServiceError) as ctx:
            svc.get_course("missing")
        self.assertEqual(ctx.exception.code, "course_not_found")


# ---------------------------------------------------------------------------
# create_course
# ---------------------------------------------------------------------------

class CreateCourseTests(Phase2TestBase):

    @patch("core.services.classroom_service.GoogleService")
    def test_create_course_success(self, MockGS):
        svc = _classroom_svc(self.admin)
        svc._google.classroom.return_value.courses.return_value.create.return_value.execute.return_value = {
            "id": "new1", "name": "Physics 101", "courseState": "ACTIVE"
        }
        result = svc.create_course(name="Physics 101")
        self.assertTrue(result["success"])
        self.assertEqual(result["course"]["name"], "Physics 101")

    @patch("core.services.classroom_service.GoogleService")
    def test_create_course_missing_name(self, MockGS):
        svc = _classroom_svc(self.admin)
        with self.assertRaises(ClassroomServiceError) as ctx:
            svc.create_course(name="")
        self.assertEqual(ctx.exception.code, "missing_name")

    @patch("core.services.classroom_service.GoogleService")
    def test_create_course_api_error(self, MockGS):
        svc = _classroom_svc(self.admin)
        svc._google.classroom.return_value.courses.return_value.create.return_value.execute.side_effect = _make_http_error(500)
        with self.assertRaises(ClassroomServiceError):
            svc.create_course(name="Bio 101")


# ---------------------------------------------------------------------------
# archive_course
# ---------------------------------------------------------------------------

class ArchiveCourseTests(Phase2TestBase):

    @patch("core.services.classroom_service.GoogleService")
    def test_archive_course_success(self, MockGS):
        svc = _classroom_svc(self.admin)
        svc._google.classroom.return_value.courses.return_value.get.return_value.execute.return_value = {
            "id": "c1", "name": "Bio", "courseState": "ACTIVE"
        }
        svc._google.classroom.return_value.courses.return_value.patch.return_value.execute.return_value = {
            "id": "c1", "courseState": "ARCHIVED"
        }
        result = svc.archive_course("c1")
        self.assertTrue(result["success"])

    @patch("core.services.classroom_service.GoogleService")
    def test_archive_course_already_archived(self, MockGS):
        svc = _classroom_svc(self.admin)
        svc._google.classroom.return_value.courses.return_value.get.return_value.execute.return_value = {
            "id": "c1", "name": "Bio", "courseState": "ARCHIVED"
        }
        result = svc.archive_course("c1")
        self.assertTrue(result["skipped"])
        self.assertEqual(result["reason"], "already_archived")

    @patch("core.services.classroom_service.GoogleService")
    def test_archive_course_deleted_course(self, MockGS):
        svc = _classroom_svc(self.admin)
        svc._google.classroom.return_value.courses.return_value.get.return_value.execute.return_value = {
            "id": "c1", "courseState": "DELETED"
        }
        with self.assertRaises(ClassroomServiceError) as ctx:
            svc.archive_course("c1")
        self.assertEqual(ctx.exception.code, "course_deleted")


# ---------------------------------------------------------------------------
# delete_course
# ---------------------------------------------------------------------------

class DeleteCourseTests(Phase2TestBase):

    @patch("core.services.classroom_service.GoogleService")
    def test_delete_archived_course_success(self, MockGS):
        svc = _classroom_svc(self.admin)
        svc._google.classroom.return_value.courses.return_value.get.return_value.execute.return_value = {
            "id": "c1", "courseState": "ARCHIVED"
        }
        svc._google.classroom.return_value.courses.return_value.delete.return_value.execute.return_value = {}
        result = svc.delete_course("c1")
        self.assertTrue(result["success"])
        self.assertTrue(result["deleted"])

    @patch("core.services.classroom_service.GoogleService")
    def test_delete_active_course_blocked(self, MockGS):
        svc = _classroom_svc(self.admin)
        svc._google.classroom.return_value.courses.return_value.get.return_value.execute.return_value = {
            "id": "c1", "courseState": "ACTIVE"
        }
        with self.assertRaises(ClassroomServiceError) as ctx:
            svc.delete_course("c1")
        self.assertEqual(ctx.exception.code, "must_archive_first")

    @patch("core.services.classroom_service.GoogleService")
    def test_delete_already_deleted_returns_skipped(self, MockGS):
        svc = _classroom_svc(self.admin)
        svc._google.classroom.return_value.courses.return_value.get.return_value.execute.return_value = {
            "id": "c1", "courseState": "ARCHIVED"
        }
        svc._google.classroom.return_value.courses.return_value.delete.return_value.execute.side_effect = _make_http_error(404)
        result = svc.delete_course("c1")
        self.assertTrue(result["skipped"])
        self.assertEqual(result["reason"], "already_deleted")


# ---------------------------------------------------------------------------
# remove_student_from_course
# ---------------------------------------------------------------------------

class RemoveStudentFromCourseTests(Phase2TestBase):

    def _svc_with_students(self, enrolled):
        svc = ClassroomRosterService(self.admin)
        svc.list_students = MagicMock(return_value=[e.lower() for e in enrolled])
        svc._google = MagicMock()
        return svc

    def test_remove_enrolled_student_success(self):
        svc = self._svc_with_students(["bob@school.com"])
        svc._google.classroom.return_value.courses.return_value.students.return_value.delete.return_value.execute.return_value = {}
        result = svc.remove_student_from_course("c1", "bob@school.com")
        self.assertTrue(result["success"])

    def test_remove_student_not_enrolled_skipped(self):
        svc = self._svc_with_students([])
        result = svc.remove_student_from_course("c1", "unknown@school.com")
        self.assertTrue(result["skipped"])
        self.assertEqual(result["reason"], "not_enrolled")

    def test_remove_student_404_returns_skipped(self):
        svc = self._svc_with_students(["bob@school.com"])
        svc._google.classroom.return_value.courses.return_value.students.return_value.delete.return_value.execute.side_effect = _make_http_error(404)
        result = svc.remove_student_from_course("c1", "bob@school.com")
        self.assertTrue(result["skipped"])


# ---------------------------------------------------------------------------
# remove_teacher_from_course
# ---------------------------------------------------------------------------

class RemoveTeacherFromCourseTests(Phase2TestBase):

    def _svc_with_teachers(self, teachers):
        svc = ClassroomRosterService(self.admin)
        svc.list_teachers = MagicMock(return_value=[t.lower() for t in teachers])
        svc._google = MagicMock()
        return svc

    def test_remove_teacher_success(self):
        svc = self._svc_with_teachers(["alice@school.com"])
        svc._google.classroom.return_value.courses.return_value.teachers.return_value.delete.return_value.execute.return_value = {}
        result = svc.remove_teacher_from_course("c1", "alice@school.com")
        self.assertTrue(result["success"])

    def test_remove_teacher_not_found_skipped(self):
        svc = self._svc_with_teachers([])
        result = svc.remove_teacher_from_course("c1", "notateacher@school.com")
        self.assertTrue(result["skipped"])
        self.assertEqual(result["reason"], "not_teacher")

    def test_remove_teacher_owner_400_error(self):
        svc = self._svc_with_teachers(["owner@school.com"])
        svc._google.classroom.return_value.courses.return_value.teachers.return_value.delete.return_value.execute.side_effect = _make_http_error(400)
        with self.assertRaises(ClassroomServiceError) as ctx:
            svc.remove_teacher_from_course("c1", "owner@school.com")
        self.assertEqual(ctx.exception.code, "cannot_remove_owner")


# ---------------------------------------------------------------------------
# Preflight validation
# ---------------------------------------------------------------------------

class PreflightTests(Phase2TestBase):

    def _svc(self):
        svc = ClassroomRosterService(self.admin)
        svc._google = MagicMock()
        return svc

    def test_preflight_create_course_valid(self):
        svc = self._svc()
        result = svc.preflight("create_course", name="Maths 101")
        self.assertTrue(result["allowed"])

    def test_preflight_create_course_missing_name(self):
        svc = self._svc()
        result = svc.preflight("create_course", name="")
        self.assertFalse(result["allowed"])
        self.assertTrue(len(result["errors"]) > 0)

    def test_preflight_archive_course_active(self):
        svc = self._svc()
        svc.get_course = MagicMock(return_value={"id": "c1", "name": "X", "courseState": "ACTIVE"})
        result = svc.preflight("archive_course", course_id="c1")
        self.assertTrue(result["allowed"])

    def test_preflight_archive_course_already_archived(self):
        svc = self._svc()
        svc.get_course = MagicMock(return_value={"id": "c1", "name": "X", "courseState": "ARCHIVED"})
        result = svc.preflight("archive_course", course_id="c1")
        self.assertFalse(result["allowed"])
        self.assertIn("already archived", result["warnings"][0])

    def test_preflight_delete_active_course(self):
        svc = self._svc()
        svc.get_course = MagicMock(return_value={"id": "c1", "name": "X", "courseState": "ACTIVE"})
        result = svc.preflight("delete_course", course_id="c1")
        self.assertFalse(result["allowed"])
        self.assertTrue(any("archived" in e.lower() for e in result["errors"]))

    def test_preflight_delete_archived_course(self):
        svc = self._svc()
        svc.get_course = MagicMock(return_value={"id": "c1", "name": "X", "courseState": "ARCHIVED"})
        result = svc.preflight("delete_course", course_id="c1")
        self.assertTrue(result["allowed"])

    def test_preflight_remove_student_enrolled(self):
        svc = self._svc()
        svc.get_course = MagicMock(return_value={"id": "c1", "name": "X"})
        svc.list_students = MagicMock(return_value=["bob@school.com"])
        result = svc.preflight("remove_student", course_id="c1", student_email="bob@school.com")
        self.assertTrue(result["allowed"])
        self.assertTrue(result["metadata"]["is_enrolled"])

    def test_preflight_remove_student_not_enrolled(self):
        svc = self._svc()
        svc.get_course = MagicMock(return_value={"id": "c1", "name": "X"})
        svc.list_students = MagicMock(return_value=[])
        result = svc.preflight("remove_student", course_id="c1", student_email="ghost@school.com")
        self.assertTrue(result["allowed"])  # warning, not error
        self.assertFalse(result["metadata"]["is_enrolled"])
        self.assertTrue(len(result["warnings"]) > 0)

    def test_preflight_remove_teacher_owner_blocked(self):
        svc = self._svc()
        svc.get_course = MagicMock(return_value={"id": "c1", "name": "X", "ownerId": "owner@school.com"})
        svc.list_teachers = MagicMock(return_value=["owner@school.com"])
        result = svc.preflight("remove_teacher", course_id="c1", teacher_email="owner@school.com")
        self.assertFalse(result["allowed"])
        self.assertTrue(any("owner" in e.lower() for e in result["errors"]))

    def test_preflight_unknown_action(self):
        svc = self._svc()
        result = svc.preflight("nonexistent_action")
        self.assertFalse(result["allowed"])


# ---------------------------------------------------------------------------
# Phase 2B Command Job builders
# ---------------------------------------------------------------------------

class Phase2BJobBuilderTests(Phase2TestBase):

    def _executor(self):
        from core.services.command_executor import CommandExecutor
        executor = CommandExecutor(self.admin)
        executor._class_service = MagicMock()
        executor._dir_service = MagicMock()
        return executor

    def test_build_remove_student_job_creates_items(self):
        ex = self._executor()
        job = ex.build_remove_student_from_course_job("c1", "bob@school.com")
        self.assertEqual(job.job_type, "REMOVE_STUDENT_FROM_COURSE")
        self.assertEqual(job.items.count(), 1)
        item = job.items.first()
        self.assertEqual(item.payload_json["course_id"], "c1")
        self.assertEqual(item.payload_json["user_email"], "bob@school.com")

    def test_build_remove_teacher_job_creates_items(self):
        ex = self._executor()
        job = ex.build_remove_teacher_from_course_job("c1", "alice@school.com")
        self.assertEqual(job.job_type, "REMOVE_TEACHER_FROM_COURSE")
        self.assertEqual(job.items.count(), 1)

    def test_build_archive_course_job(self):
        ex = self._executor()
        job = ex.build_archive_course_job("c99")
        self.assertEqual(job.job_type, "ARCHIVE_COURSE")
        self.assertEqual(job.items.first().payload_json["course_id"], "c99")

    def test_build_delete_course_job(self):
        ex = self._executor()
        job = ex.build_delete_course_job("c99")
        self.assertEqual(job.job_type, "DELETE_COURSE")

    def test_execute_remove_student_dispatches_service(self):
        from core.models import CommandJobItem, TargetType, ActionType, ItemStatus
        ex = self._executor()
        ex._class_service.remove_student_from_course.return_value = {"success": True, "email": "s@x.com"}
        job = ex.build_remove_student_from_course_job("c1", "s@x.com")
        summary = ex.execute_job(job)
        ex._class_service.remove_student_from_course.assert_called_once_with("c1", "s@x.com")
        self.assertEqual(summary["success"], 1)

    def test_execute_remove_teacher_dispatches_service(self):
        ex = self._executor()
        ex._class_service.remove_teacher_from_course.return_value = {"success": True}
        job = ex.build_remove_teacher_from_course_job("c1", "t@x.com")
        summary = ex.execute_job(job)
        ex._class_service.remove_teacher_from_course.assert_called_once_with("c1", "t@x.com")

    def test_execute_archive_course_dispatches_service(self):
        ex = self._executor()
        ex._class_service.archive_course.return_value = {"success": True}
        job = ex.build_archive_course_job("c1")
        ex.execute_job(job)
        ex._class_service.archive_course.assert_called_once_with("c1")

    def test_execute_delete_course_dispatches_service(self):
        ex = self._executor()
        ex._class_service.delete_course.return_value = {"success": True, "deleted": True}
        job = ex.build_delete_course_job("c1")
        ex.execute_job(job)
        ex._class_service.delete_course.assert_called_once_with("c1")


# ---------------------------------------------------------------------------
# Phase 2B Preview methods
# ---------------------------------------------------------------------------

class Phase2BPreviewTests(Phase2TestBase):

    def _executor(self):
        from core.services.command_executor import CommandExecutor
        executor = CommandExecutor(self.admin)
        executor._class_service = MagicMock()
        return executor

    def test_preview_create_course(self):
        ex = self._executor()
        ex._class_service.preflight.return_value = {"allowed": True, "warnings": [], "errors": [], "metadata": {}}
        result = ex.preview_create_course("New Course")
        self.assertTrue(result["allowed"])
        self.assertEqual(result["name"], "New Course")

    def test_preview_archive_course(self):
        ex = self._executor()
        ex._class_service.preflight.return_value = {"allowed": True, "warnings": [], "errors": [], "metadata": {"current_state": "ACTIVE"}}
        result = ex.preview_archive_course("c1")
        self.assertTrue(result["allowed"])
        self.assertEqual(result["course_id"], "c1")

    def test_preview_remove_student(self):
        ex = self._executor()
        ex._class_service.preflight.return_value = {"allowed": True, "warnings": [], "errors": [], "metadata": {"is_enrolled": True}}
        result = ex.preview_remove_student("c1", "bob@school.com")
        self.assertTrue(result["allowed"])
        self.assertEqual(result["user_email"], "bob@school.com")

    def test_preview_remove_teacher_owner_blocked(self):
        ex = self._executor()
        ex._class_service.preflight.return_value = {"allowed": False, "warnings": [], "errors": ["Cannot remove owner"], "metadata": {}}
        result = ex.preview_remove_teacher("c1", "owner@school.com")
        self.assertFalse(result["allowed"])


# ---------------------------------------------------------------------------
# Phase 2B API endpoint tests
# ---------------------------------------------------------------------------

class Phase2BAPITests(Phase2TestBase):

    @patch("core.admin_views.ClassroomRosterService")
    def test_preflight_endpoint_success(self, MockSvc):
        MockSvc.return_value.preflight.return_value = {
            "allowed": True, "warnings": [], "errors": [], "metadata": {}
        }
        resp = self.client.post(
            "/api/classroom/preflight",
            {"action": "create_course", "name": "Test Course"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["allowed"])

    @patch("core.admin_views.ClassroomRosterService")
    def test_course_roster_endpoint(self, MockSvc):
        MockSvc.return_value.list_students.return_value = ["s1@x.com", "s2@x.com"]
        MockSvc.return_value.list_teachers.return_value = ["t1@x.com"]
        resp = self.client.get("/api/classroom/courses/c1/roster")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["student_count"], 2)
        self.assertEqual(resp.json()["teacher_count"], 1)

    @patch("core.admin_views.ClassroomRosterService")
    def test_create_course_endpoint(self, MockSvc):
        MockSvc.return_value.create_course.return_value = {
            "success": True, "course": {"id": "new1", "name": "Maths 101"}
        }
        resp = self.client.post(
            "/api/classroom/courses/create",
            {"name": "Maths 101"},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(resp.json()["success"])

    @patch("core.admin_views.ClassroomRosterService")
    def test_create_course_missing_name_400(self, MockSvc):
        resp = self.client.post(
            "/api/classroom/courses/create",
            {},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    @patch("core.admin_views.ClassroomRosterService")
    def test_archive_course_endpoint(self, MockSvc):
        MockSvc.return_value.archive_course.return_value = {"success": True, "course": {"id": "c1"}}
        resp = self.client.post(
            "/api/classroom/courses/c1/archive",
            format="json",
        )
        self.assertEqual(resp.status_code, 200)

    @patch("core.admin_views.ClassroomRosterService")
    def test_archive_course_error_returns_400(self, MockSvc):
        MockSvc.return_value.archive_course.side_effect = ClassroomServiceError("Already deleted", "course_deleted")
        resp = self.client.post(
            "/api/classroom/courses/c1/archive",
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "course_deleted")

    @patch("core.admin_views.ClassroomRosterService")
    def test_delete_course_endpoint(self, MockSvc):
        MockSvc.return_value.delete_course.return_value = {"success": True, "deleted": True, "course_id": "c1"}
        resp = self.client.delete("/api/classroom/courses/c1")
        self.assertEqual(resp.status_code, 200)

    @patch("core.admin_views.ClassroomRosterService")
    def test_delete_active_course_returns_400(self, MockSvc):
        MockSvc.return_value.delete_course.side_effect = ClassroomServiceError("Must archive first", "must_archive_first")
        resp = self.client.delete("/api/classroom/courses/c1")
        self.assertEqual(resp.status_code, 400)

    @patch("core.admin_views.ClassroomRosterService")
    def test_remove_student_endpoint(self, MockSvc):
        MockSvc.return_value.remove_student_from_course.return_value = {"success": True, "email": "s@x.com"}
        resp = self.client.post(
            "/api/classroom/remove-student",
            {"course_id": "c1", "student_email": "s@x.com"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["success"])

    @patch("core.admin_views.ClassroomRosterService")
    def test_remove_teacher_endpoint(self, MockSvc):
        MockSvc.return_value.remove_teacher_from_course.return_value = {"success": True, "email": "t@x.com"}
        resp = self.client.post(
            "/api/classroom/remove-teacher",
            {"course_id": "c1", "teacher_email": "t@x.com"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)

    @patch("core.admin_views.ClassroomRosterService")
    def test_remove_teacher_owner_returns_400(self, MockSvc):
        MockSvc.return_value.remove_teacher_from_course.side_effect = ClassroomServiceError("Cannot remove owner", "cannot_remove_owner")
        resp = self.client.post(
            "/api/classroom/remove-teacher",
            {"course_id": "c1", "teacher_email": "owner@x.com"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "cannot_remove_owner")

    def test_phase2b_endpoints_require_admin(self):
        """Non-staff user should get 403 on all Phase 2B endpoints."""
        self.client.force_authenticate(self.regular_user)
        endpoints = [
            ("post", "/api/classroom/preflight", {"action": "create_course", "name": "x"}),
            ("get", "/api/classroom/courses/c1/roster", {}),
            ("post", "/api/classroom/courses/create", {"name": "x"}),
            ("post", "/api/classroom/courses/c1/archive", {}),
            ("delete", "/api/classroom/courses/c1", {}),
            ("post", "/api/classroom/remove-student", {"course_id": "c1", "student_email": "s@x.com"}),
            ("post", "/api/classroom/remove-teacher", {"course_id": "c1", "teacher_email": "t@x.com"}),
        ]
        for method, url, data in endpoints:
            if method == "get":
                resp = self.client.get(url)
            else:
                resp = getattr(self.client, method)(url, data, format="json")
            self.assertEqual(resp.status_code, 403, f"Expected 403 for {method.upper()} {url}")

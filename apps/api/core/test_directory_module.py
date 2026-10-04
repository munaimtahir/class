import json
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import (
    ApprovalActionType,
    ApprovalExecutionStatus,
    ApprovalRequest,
    ApprovalRequestStatus,
    DirectoryAuditLog,
    DirectoryIssue,
    DirectoryIssueStatus,
    DirectoryIssueType,
    DirectoryUser,
    OrgUnitTemplate,
    EmailTemplateRule,
    ProvisioningStatus,
    UserRole,
)
from .google_scopes import SCOPE_ADMIN_USER
from .services.directory_module_service import ExpectedStateResolver, InconsistencyDetectionService
from .services.google_directory_service import DirectoryServiceError, GoogleDirectoryService

User = get_user_model()


def make_user(email: str, role: str = UserRole.OPERATOR, is_staff: bool = False):
    return User.objects.create_user(email=email, password="testpass123", role=role, is_staff=is_staff)


class DirectorySyncApiTests(TestCase):
    def setUp(self):
        self.user = make_user("operator@school.edu", role=UserRole.OPERATOR)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    @patch("core.services.directory_module_service.GoogleDirectoryService.iter_user_pages")
    def test_directory_sync_creates_and_updates_cache(self, iter_user_pages_mock):
        iter_user_pages_mock.return_value = [[
            {
                "id": "g-1",
                "primaryEmail": "student1@school.edu",
                "name": {"fullName": "Student One", "givenName": "Student", "familyName": "One"},
                "orgUnitPath": "/Students/Year1",
                "suspended": False,
                "archived": False,
                "aliases": ["s.one@school.edu"],
                "phones": [{"value": "+1 (555) 123-4567"}],
            }
        ]]
        resp = self.client.post("/api/directory/sync", {"max_results": 10}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(DirectoryUser.objects.count(), 1)
        self.assertEqual(DirectoryUser.objects.first().primary_email, "student1@school.edu")
        first_user = DirectoryUser.objects.first()
        self.assertEqual(first_user.normalized_phone, "5551234567")
        self.assertEqual(resp.data["pages_fetched"], 1)
        self.assertEqual(resp.data["total_directory_users"], 1)

        iter_user_pages_mock.return_value = [[
            {
                "id": "g-1",
                "primaryEmail": "student1@school.edu",
                "name": {"fullName": "Student One Updated", "givenName": "Student", "familyName": "One"},
                "orgUnitPath": "/Students/Year2",
                "suspended": False,
                "archived": False,
            }
        ]]
        resp2 = self.client.post("/api/directory/sync", {"max_results": 10}, format="json")
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(DirectoryUser.objects.count(), 1)
        user = DirectoryUser.objects.get(google_user_id="g-1")
        self.assertEqual(user.org_unit_path, "/Students/Year2")
        self.assertEqual(user.normalized_email, "student1@school.edu")
        self.assertEqual(user.normalized_full_name, "student one updated")

    @patch("core.services.directory_module_service.GoogleDirectoryService.iter_user_pages")
    def test_directory_sync_returns_400_for_directory_service_errors(self, iter_user_pages_mock):
        iter_user_pages_mock.side_effect = DirectoryServiceError(
            "Permission denied by Google Directory API.",
            "forbidden",
        )

        resp = self.client.post("/api/directory/sync", {"max_results": 10}, format="json")

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            resp.json(),
            {
                "detail": "Permission denied by Google Directory API.",
                "code": "forbidden",
            },
        )


def _make_http_error(status_code: int, *, message: str, reason: str):
    from googleapiclient.errors import HttpError

    resp = MagicMock()
    resp.status = status_code
    content = json.dumps(
        {
            "error": {
                "code": status_code,
                "message": message,
                "errors": [{"message": message, "reason": reason}],
            }
        }
    ).encode()
    return HttpError(resp=resp, content=content)


class GoogleDirectoryServiceErrorTests(TestCase):
    def test_normalize_http_error_for_api_not_enabled(self):
        svc = GoogleDirectoryService(user=MagicMock())
        err = _make_http_error(
            403,
            message="Admin SDK API has not been used in project before or it is disabled.",
            reason="accessNotConfigured",
        )

        normalized = svc._normalize_http_error(err)

        self.assertEqual(normalized.code, "api_not_enabled")
        self.assertEqual(
            str(normalized),
            "Google Admin SDK API is not enabled for the configured Google Cloud project.",
        )

    def test_normalize_http_error_for_insufficient_scopes(self):
        svc = GoogleDirectoryService(user=MagicMock())
        err = _make_http_error(
            403,
            message="Request had insufficient authentication scopes.",
            reason="insufficientPermissions",
        )

        normalized = svc._normalize_http_error(err)

        self.assertEqual(normalized.code, "insufficient_scopes")
        self.assertEqual(
            str(normalized),
            "Google OAuth token is missing the required Admin SDK Directory scopes.",
        )


class RuleResolutionTests(TestCase):
    def test_ou_rule_resolution(self):
        user = DirectoryUser.objects.create(
            google_user_id="u-1",
            primary_email="user@school.edu",
            full_name="User One",
            user_category="student",
            department="Medicine",
            program="MBBS",
            batch="2026",
        )
        OrgUnitTemplate.objects.create(
            name="Student MBBS 2026",
            user_category="student",
            department="Medicine",
            program="MBBS",
            batch="2026",
            target_org_unit_path="/Students/MBBS/2026",
            priority=1,
        )
        resolver = ExpectedStateResolver()
        result = resolver.resolve(user)
        self.assertEqual(result.expected_org_unit_path, "/Students/MBBS/2026")

    def test_email_template_validation_detection(self):
        user = DirectoryUser.objects.create(
            google_user_id="u-2",
            primary_email="wrong@school.edu",
            full_name="Alice Brown",
            given_name="Alice",
            family_name="Brown",
            user_category="student",
            external_identifier="1001",
        )
        OrgUnitTemplate.objects.create(
            name="Student Default",
            user_category="student",
            target_org_unit_path="/Students",
            priority=1,
        )
        EmailTemplateRule.objects.create(
            name="Student Email",
            user_category="student",
            email_pattern="{given_name}.{family_name}",
            domain="school.edu",
            priority=1,
        )
        result = InconsistencyDetectionService().scan(users=DirectoryUser.objects.filter(id=user.id))
        self.assertGreaterEqual(result["issues_created"], 1)
        self.assertTrue(
            DirectoryIssue.objects.filter(
                directory_user=user, issue_type=DirectoryIssueType.INVALID_EMAIL_PATTERN
            ).exists()
        )


class IssueLifecycleApiTests(TestCase):
    def setUp(self):
        self.user = make_user("operator2@school.edu", role=UserRole.OPERATOR)
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.dir_user = DirectoryUser.objects.create(
            google_user_id="u-3",
            primary_email="student3@school.edu",
            full_name="Student Three",
            user_category="student",
        )
        self.issue = DirectoryIssue.objects.create(
            directory_user=self.dir_user,
            issue_type=DirectoryIssueType.INVALID_ORG_UNIT,
            severity="warning",
            actual_value="/Wrong",
            expected_value="/Students/2026",
            suggested_action="move_ou",
        )

    def test_issue_status_transitions(self):
        resp = self.client.post(f"/api/directory/issues/{self.issue.id}/approve", {}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.issue.refresh_from_db()
        self.assertEqual(self.issue.status, DirectoryIssueStatus.APPROVED)

        resp2 = self.client.post(f"/api/directory/issues/{self.issue.id}/mark-exception", {}, format="json")
        self.assertEqual(resp2.status_code, 200)
        self.issue.refresh_from_db()
        self.assertEqual(self.issue.status, DirectoryIssueStatus.EXCEPTION_MARKED)


class ChangeJobApiTests(TestCase):
    def setUp(self):
        self.admin = make_user("admin@school.edu", role=UserRole.ADMIN)
        self.client = APIClient()
        self.client.force_authenticate(self.admin)
        self.dir_user = DirectoryUser.objects.create(
            google_user_id="u-4",
            primary_email="student4@school.edu",
            full_name="Student Four",
            user_category="student",
            org_unit_path="/Wrong",
        )
        self.issue = DirectoryIssue.objects.create(
            directory_user=self.dir_user,
            issue_type=DirectoryIssueType.INVALID_ORG_UNIT,
            severity="warning",
            actual_value="/Wrong",
            expected_value="/Students/2026",
            suggested_action="move_ou",
            status=DirectoryIssueStatus.APPROVED,
        )

    def test_change_job_preview_path(self):
        resp = self.client.post(
            "/api/directory/change-jobs/preview",
            {"job_type": "ou_correction", "scope_type": "issue_selection", "issue_ids": [self.issue.id]},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["status"], "preview_ready")
        self.assertEqual(resp.data["item_count"], 1)

    @patch("core.services.directory_module_service.GoogleDirectoryService.move_user_to_org_unit")
    def test_change_job_execution_path_safe_action(self, move_mock):
        move_mock.return_value = {"success": True, "user": {"id": "g-user-4"}}
        preview = self.client.post(
            "/api/directory/change-jobs/preview",
            {"job_type": "ou_correction", "scope_type": "issue_selection", "issue_ids": [self.issue.id]},
            format="json",
        )
        self.assertEqual(preview.status_code, 201)
        exec_resp = self.client.post(
            "/api/directory/change-jobs/execute",
            {"preview_job_id": preview.data["id"], "dry_run": False, "async": False},
            format="json",
        )
        self.assertEqual(exec_resp.status_code, 200)
        self.assertIn(exec_resp.data["status"], ["completed", "partial"])
        self.assertTrue(DirectoryAuditLog.objects.filter(action_type="move_ou").exists())


class ProvisioningApiTests(TestCase):
    def setUp(self):
        self.admin = make_user("admin-prov@school.edu", role=UserRole.ADMIN)
        self.client = APIClient()
        self.client.force_authenticate(self.admin)
        OrgUnitTemplate.objects.create(
            name="Student template",
            user_category="student",
            target_org_unit_path="/Students/2026",
            priority=1,
        )
        EmailTemplateRule.objects.create(
            name="Student email",
            user_category="student",
            email_pattern="{given_name}.{family_name}",
            domain="school.edu",
            collision_strategy="append_numeric",
            priority=1,
        )

    def test_provisioning_preview_path(self):
        resp = self.client.post(
            "/api/provisioning/preview",
            {
                "full_name": "Alice Brown",
                "user_category": "student",
                "source_identifier": "1009",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertIn("generated_email", resp.data)
        self.assertEqual(resp.data["status"], "previewed")

    @patch("core.services.directory_module_service.GoogleDirectoryService.create_user")
    def test_provisioning_create_path_and_audit(self, create_user_mock):
        create_user_mock.return_value = {
            "success": True,
            "user": {
                "id": "google-u-1009",
                "primaryEmail": "alice.brown@school.edu",
                "orgUnitPath": "/Students/2026",
                "name": {"fullName": "Alice Brown", "givenName": "Alice", "familyName": "Brown"},
            },
        }
        preview = self.client.post(
            "/api/provisioning/preview",
            {"full_name": "Alice Brown", "user_category": "student", "source_identifier": "1009"},
            format="json",
        )
        self.assertEqual(preview.status_code, 201)
        execute = self.client.post(
            "/api/provisioning/create",
            {"preview_record_id": preview.data["id"]},
            format="json",
        )
        self.assertEqual(execute.status_code, 200)
        self.assertEqual(execute.data["status"], ProvisioningStatus.EXECUTED)
        self.assertTrue(DirectoryAuditLog.objects.filter(action_type="create_user").exists())


class RoleAndValidationTests(TestCase):
    def setUp(self):
        self.viewer = make_user("viewer@school.edu", role=UserRole.VIEWER)
        self.operator = make_user("operator@school.edu", role=UserRole.OPERATOR)

    def test_role_restriction_for_rule_edits(self):
        client = APIClient()
        client.force_authenticate(self.viewer)
        resp = client.post(
            "/api/org-units/templates",
            {"name": "X", "user_category": "student", "target_org_unit_path": "/Students"},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_api_validation_errors(self):
        client = APIClient()
        client.force_authenticate(self.operator)
        bad_preview = client.post("/api/provisioning/preview", {"user_category": "student"}, format="json")
        self.assertEqual(bad_preview.status_code, 400)

        bad_job = client.post(
            "/api/directory/change-jobs/preview",
            {"job_type": "ou_correction", "scope_type": "issue_selection"},
            format="json",
        )
        self.assertEqual(bad_job.status_code, 400)

    def test_bulk_change_execution_requires_approval(self):
        dir_user = DirectoryUser.objects.create(
            google_user_id="u-9",
            primary_email="student9@school.edu",
            full_name="Student Nine",
            user_category="student",
        )
        issue = DirectoryIssue.objects.create(
            directory_user=dir_user,
            issue_type=DirectoryIssueType.INVALID_ORG_UNIT,
            severity="warning",
            actual_value="/Wrong",
            expected_value="/Students/2026",
            suggested_action="move_ou",
            status=DirectoryIssueStatus.APPROVED,
        )
        client = APIClient()
        client.force_authenticate(self.operator)
        preview = client.post(
            "/api/directory/change-jobs/preview",
            {"job_type": "ou_correction", "scope_type": "bulk", "issue_ids": [issue.id]},
            format="json",
        )
        self.assertEqual(preview.status_code, 201)
        execute = client.post(
            "/api/directory/change-jobs/execute",
            {"preview_job_id": preview.data["id"], "dry_run": False, "async": False},
            format="json",
        )
        self.assertEqual(execute.status_code, 400)
        self.assertIn("approval_request_id", execute.json()["detail"])


class ApprovalWorkflowTests(TestCase):
    def setUp(self):
        self.operator = make_user("operator-approval@school.edu", role=UserRole.OPERATOR)
        self.admin = make_user("admin-approval@school.edu", role=UserRole.ADMIN)
        self.operator.google_scopes_json = [SCOPE_ADMIN_USER]
        self.operator.google_scopes = SCOPE_ADMIN_USER
        self.operator.save(update_fields=["google_scopes_json", "google_scopes"])
        self.admin.google_scopes_json = [SCOPE_ADMIN_USER]
        self.admin.google_scopes = SCOPE_ADMIN_USER
        self.admin.save(update_fields=["google_scopes_json", "google_scopes"])
        self.operator_client = APIClient()
        self.operator_client.force_authenticate(self.operator)
        self.admin_client = APIClient()
        self.admin_client.force_authenticate(self.admin)
        self.dir_user = DirectoryUser.objects.create(
            google_user_id="u-12",
            primary_email="student12@school.edu",
            full_name="Student Twelve",
            user_category="student",
            org_unit_path="/Wrong",
        )
        self.issue = DirectoryIssue.objects.create(
            directory_user=self.dir_user,
            issue_type=DirectoryIssueType.INVALID_ORG_UNIT,
            severity="warning",
            actual_value="/Wrong",
            expected_value="/Students/2026",
            suggested_action="move_ou",
            status=DirectoryIssueStatus.APPROVED,
        )
        OrgUnitTemplate.objects.create(
            name="Student template",
            user_category="student",
            target_org_unit_path="/Students/2026",
            priority=1,
        )
        EmailTemplateRule.objects.create(
            name="Student email",
            user_category="student",
            email_pattern="{given_name}.{family_name}",
            domain="school.edu",
            collision_strategy="append_numeric",
            priority=1,
        )

    @patch("core.services.directory_module_service.GoogleDirectoryService.move_user_to_org_unit")
    def test_approval_request_creation_approval_and_execution_linkage(self, move_mock):
        move_mock.return_value = {"success": True, "user": {"id": "google-12"}}
        preview = self.operator_client.post(
            "/api/directory/change-jobs/preview",
            {"job_type": "ou_correction", "scope_type": "bulk", "issue_ids": [self.issue.id]},
            format="json",
        )
        self.assertEqual(preview.status_code, 201)

        req_resp = self.operator_client.post(
            "/api/directory/approvals",
            {
                "action_type": ApprovalActionType.BULK_CHANGE_JOB_EXECUTE,
                "target_type": "change_job",
                "target_reference": f"change_job:{preview.data['id']}",
                "payload": {"preview_job_id": preview.data["id"]},
                "linked_change_job_id": preview.data["id"],
            },
            format="json",
        )
        self.assertEqual(req_resp.status_code, 201)
        approval_id = req_resp.data["id"]
        approval = ApprovalRequest.objects.get(id=approval_id)
        self.assertEqual(approval.status, ApprovalRequestStatus.PENDING)

        reject_non_admin = self.operator_client.post(
            f"/api/directory/approvals/{approval_id}/approve",
            {"review_notes": "no"},
            format="json",
        )
        self.assertEqual(reject_non_admin.status_code, 403)

        approve_resp = self.admin_client.post(
            f"/api/directory/approvals/{approval_id}/approve",
            {"review_notes": "approved for bulk move"},
            format="json",
        )
        self.assertEqual(approve_resp.status_code, 200)

        execute = self.operator_client.post(
            "/api/directory/change-jobs/execute",
            {"preview_job_id": preview.data["id"], "approval_request_id": approval_id, "dry_run": False, "async": False},
            format="json",
        )
        self.assertEqual(execute.status_code, 200)
        approval.refresh_from_db()
        self.assertEqual(approval.status, ApprovalRequestStatus.EXECUTED)
        self.assertEqual(approval.execution_status, ApprovalExecutionStatus.EXECUTED)
        self.assertTrue(DirectoryAuditLog.objects.filter(approval_request=approval).exists())

    def test_rejected_approval_blocks_execution(self):
        preview = self.operator_client.post(
            "/api/directory/change-jobs/preview",
            {"job_type": "ou_correction", "scope_type": "bulk", "issue_ids": [self.issue.id]},
            format="json",
        )
        self.assertEqual(preview.status_code, 201)
        req_resp = self.operator_client.post(
            "/api/directory/approvals",
            {
                "action_type": ApprovalActionType.BULK_CHANGE_JOB_EXECUTE,
                "target_type": "change_job",
                "target_reference": f"change_job:{preview.data['id']}",
                "payload": {"preview_job_id": preview.data["id"]},
                "linked_change_job_id": preview.data["id"],
            },
            format="json",
        )
        approval_id = req_resp.data["id"]
        reject_resp = self.admin_client.post(
            f"/api/directory/approvals/{approval_id}/reject",
            {"review_notes": "policy denied"},
            format="json",
        )
        self.assertEqual(reject_resp.status_code, 200)
        execute = self.operator_client.post(
            "/api/directory/change-jobs/execute",
            {"preview_job_id": preview.data["id"], "approval_request_id": approval_id, "dry_run": False, "async": False},
            format="json",
        )
        self.assertEqual(execute.status_code, 400)
        self.assertIn("expected approved", execute.json()["detail"])

    @patch("core.directory_views.execute_provisioning_records_task.delay")
    def test_bulk_provisioning_requires_and_uses_approval(self, delay_mock):
        class _MockTask:
            id = "task-123"

        delay_mock.return_value = _MockTask()
        first = self.operator_client.post(
            "/api/provisioning/preview",
            {"full_name": "One Student", "user_category": "student", "source_identifier": "s-1"},
            format="json",
        )
        second = self.operator_client.post(
            "/api/provisioning/preview",
            {"full_name": "Two Student", "user_category": "student", "source_identifier": "s-2"},
            format="json",
        )
        ids = [first.data["id"], second.data["id"]]
        blocked = self.operator_client.post(
            "/api/provisioning/bulk-create",
            {"preview_record_ids": ids},
            format="json",
        )
        self.assertEqual(blocked.status_code, 400)
        self.assertIn("approval_request_id", blocked.json()["detail"])

        req_resp = self.operator_client.post(
            "/api/directory/approvals",
            {
                "action_type": ApprovalActionType.BULK_PROVISIONING_CREATE,
                "target_type": "provisioning_batch",
                "target_reference": f"records:{','.join(str(i) for i in ids)}",
                "payload": {"preview_record_ids": ids},
            },
            format="json",
        )
        approval_id = req_resp.data["id"]
        self.admin_client.post(
            f"/api/directory/approvals/{approval_id}/approve",
            {"review_notes": "approved"},
            format="json",
        )
        queued = self.operator_client.post(
            "/api/provisioning/bulk-create",
            {"preview_record_ids": ids, "approval_request_id": approval_id},
            format="json",
        )
        self.assertEqual(queued.status_code, 202)
        delay_mock.assert_called_once()

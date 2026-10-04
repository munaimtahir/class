import secrets
import string
import re
from dataclasses import dataclass
from typing import Iterable, Optional

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from core.models import (
    ApprovalExecutionStatus,
    ApprovalRequest,
    ApprovalRequestStatus,
    DirectoryAuditLog,
    DirectoryChangeJob,
    DirectoryChangeJobItem,
    DirectoryChangeJobStatus,
    DirectoryChangeJobType,
    DirectoryIssue,
    DirectoryIssueStatus,
    DirectoryIssueType,
    DirectorySyncJob,
    DirectorySyncJobStatus,
    DirectoryUser,
    EmailCollisionStrategy,
    EmailTemplateRule,
    IssueSeverity,
    ItemStatus,
    OrgUnitTemplate,
    ProvisioningMode,
    ProvisioningRecord,
    ProvisioningStatus,
)
from core.services.google_directory_service import DirectoryServiceError, GoogleDirectoryService


class DirectoryModuleError(Exception):
    def __init__(self, message: str, code: str = "directory_module_error"):
        super().__init__(message)
        self.code = code


def normalize_email(value: str) -> str:
    return (value or "").strip().lower()


def normalize_name(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", (value or "").strip())
    return cleaned.lower()


def normalize_phone(value: str) -> str:
    digits = re.sub(r"\D+", "", (value or ""))
    if not digits:
        return ""
    if len(digits) > 10:
        digits = digits[-10:]
    return digits


class DirectoryAuditService:
    @staticmethod
    def log(
        *,
        actor,
        action_type: str,
        target_type: str,
        target_ref: str,
        is_dry_run: bool,
        success: bool,
        before_json: Optional[dict] = None,
        after_json: Optional[dict] = None,
        request_json: Optional[dict] = None,
        response_json: Optional[dict] = None,
        error_message: str = "",
        external_reference: str = "",
        correlation_id: str = "",
        approval_request: Optional[ApprovalRequest] = None,
        linked_change_job: Optional[DirectoryChangeJob] = None,
        linked_provisioning_record: Optional[ProvisioningRecord] = None,
    ) -> DirectoryAuditLog:
        return DirectoryAuditLog.objects.create(
            actor=actor,
            action_type=action_type,
            target_type=target_type,
            target_ref=target_ref,
            is_dry_run=is_dry_run,
            success=success,
            before_json=before_json or {},
            after_json=after_json or {},
            request_json=request_json or {},
            response_json=response_json or {},
            error_message=error_message,
            external_reference=external_reference,
            correlation_id=correlation_id,
            approval_request=approval_request,
            linked_change_job=linked_change_job,
            linked_provisioning_record=linked_provisioning_record,
        )


class ApprovalService:
    @staticmethod
    @transaction.atomic
    def create_request(
        *,
        requested_by,
        action_type: str,
        target_type: str,
        target_reference: str,
        payload: Optional[dict] = None,
        linked_change_job: Optional[DirectoryChangeJob] = None,
        linked_provisioning_record: Optional[ProvisioningRecord] = None,
    ) -> ApprovalRequest:
        approval = ApprovalRequest.objects.create(
            action_type=action_type,
            target_type=target_type,
            target_reference=target_reference,
            payload=payload or {},
            requested_by=requested_by,
            linked_change_job=linked_change_job,
            linked_provisioning_record=linked_provisioning_record,
        )
        DirectoryAuditService.log(
            actor=requested_by,
            action_type="approval_request_created",
            target_type=target_type,
            target_ref=target_reference,
            is_dry_run=False,
            success=True,
            request_json=payload or {},
            response_json={"approval_request_id": approval.id},
            approval_request=approval,
            linked_change_job=linked_change_job,
            linked_provisioning_record=linked_provisioning_record,
            correlation_id=f"approval-create-{approval.id}",
        )
        return approval

    @staticmethod
    @transaction.atomic
    def approve(*, approval: ApprovalRequest, reviewer, review_notes: str = "") -> ApprovalRequest:
        if approval.status != ApprovalRequestStatus.PENDING:
            raise DirectoryModuleError("Only pending approval requests can be approved.", "approval_invalid_state")
        approval.status = ApprovalRequestStatus.APPROVED
        approval.execution_status = ApprovalExecutionStatus.READY_TO_EXECUTE
        approval.reviewed_by = reviewer
        approval.reviewed_at = timezone.now()
        approval.review_notes = review_notes
        approval.execution_message = ""
        approval.save(
            update_fields=[
                "status",
                "execution_status",
                "reviewed_by",
                "reviewed_at",
                "review_notes",
                "execution_message",
                "updated_at",
            ]
        )
        DirectoryAuditService.log(
            actor=reviewer,
            action_type="approval_request_approved",
            target_type=approval.target_type,
            target_ref=approval.target_reference,
            is_dry_run=False,
            success=True,
            request_json={"review_notes": review_notes},
            response_json={"approval_request_id": approval.id},
            approval_request=approval,
            linked_change_job=approval.linked_change_job,
            linked_provisioning_record=approval.linked_provisioning_record,
            correlation_id=f"approval-approve-{approval.id}",
        )
        return approval

    @staticmethod
    @transaction.atomic
    def reject(*, approval: ApprovalRequest, reviewer, review_notes: str = "") -> ApprovalRequest:
        if approval.status != ApprovalRequestStatus.PENDING:
            raise DirectoryModuleError("Only pending approval requests can be rejected.", "approval_invalid_state")
        approval.status = ApprovalRequestStatus.REJECTED
        approval.execution_status = ApprovalExecutionStatus.NOT_STARTED
        approval.reviewed_by = reviewer
        approval.reviewed_at = timezone.now()
        approval.review_notes = review_notes
        approval.execution_message = review_notes
        approval.save(
            update_fields=[
                "status",
                "execution_status",
                "reviewed_by",
                "reviewed_at",
                "review_notes",
                "execution_message",
                "updated_at",
            ]
        )
        DirectoryAuditService.log(
            actor=reviewer,
            action_type="approval_request_rejected",
            target_type=approval.target_type,
            target_ref=approval.target_reference,
            is_dry_run=False,
            success=True,
            request_json={"review_notes": review_notes},
            response_json={"approval_request_id": approval.id},
            approval_request=approval,
            linked_change_job=approval.linked_change_job,
            linked_provisioning_record=approval.linked_provisioning_record,
            correlation_id=f"approval-reject-{approval.id}",
        )
        return approval

    @staticmethod
    @transaction.atomic
    def cancel(*, approval: ApprovalRequest, actor, review_notes: str = "") -> ApprovalRequest:
        if approval.status != ApprovalRequestStatus.PENDING:
            raise DirectoryModuleError("Only pending approval requests can be cancelled.", "approval_invalid_state")
        approval.status = ApprovalRequestStatus.CANCELLED
        approval.execution_status = ApprovalExecutionStatus.NOT_STARTED
        approval.reviewed_by = actor
        approval.reviewed_at = timezone.now()
        approval.review_notes = review_notes
        approval.execution_message = review_notes
        approval.save(
            update_fields=[
                "status",
                "execution_status",
                "reviewed_by",
                "reviewed_at",
                "review_notes",
                "execution_message",
                "updated_at",
            ]
        )
        DirectoryAuditService.log(
            actor=actor,
            action_type="approval_request_cancelled",
            target_type=approval.target_type,
            target_ref=approval.target_reference,
            is_dry_run=False,
            success=True,
            request_json={"review_notes": review_notes},
            response_json={"approval_request_id": approval.id},
            approval_request=approval,
            linked_change_job=approval.linked_change_job,
            linked_provisioning_record=approval.linked_provisioning_record,
            correlation_id=f"approval-cancel-{approval.id}",
        )
        return approval


def _normalize_fragment(value: str) -> str:
    if not value:
        return ""
    chars = [c.lower() for c in value if c.isalnum()]
    return "".join(chars)


def _split_name(full_name: str) -> tuple[str, str]:
    parts = [p for p in full_name.strip().split() if p]
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


@dataclass
class ExpectedState:
    expected_org_unit_path: str
    expected_email: str
    email_rule_id: Optional[int]
    org_template_id: Optional[int]


class ExpectedStateResolver:
    CONTEXT_FIELDS = ("department", "program", "batch", "year")

    def _template_matches_user(self, template, user: DirectoryUser) -> bool:
        for field in self.CONTEXT_FIELDS:
            expected = (getattr(template, field, "") or "").strip()
            actual = (getattr(user, field, "") or "").strip()
            if expected and expected != actual:
                return False
        return True

    def resolve_org_unit_template(self, user: DirectoryUser) -> Optional[OrgUnitTemplate]:
        templates = OrgUnitTemplate.objects.filter(
            is_active=True, user_category=user.user_category
        ).order_by("priority", "id")
        for template in templates:
            if self._template_matches_user(template, user):
                return template
        return None

    def resolve_email_rule(self, user: DirectoryUser) -> Optional[EmailTemplateRule]:
        rules = EmailTemplateRule.objects.filter(
            is_active=True, user_category=user.user_category
        ).order_by("priority", "id")
        for rule in rules:
            if self._template_matches_user(rule, user):
                return rule
        return None

    def _build_local_part(self, user: DirectoryUser, pattern: str) -> str:
        given = _normalize_fragment(user.given_name)
        family = _normalize_fragment(user.family_name)
        full = _normalize_fragment(user.full_name)
        identifier = _normalize_fragment(
            user.external_identifier or user.roll_number or user.employee_id
        )
        local = pattern.format(
            given_name=given,
            family_name=family,
            full_name=full,
            identifier=identifier,
        )
        local = local.replace("..", ".").strip(".")
        return local.lower()

    def generate_expected_email(
        self,
        user: DirectoryUser,
        rule: EmailTemplateRule,
        check_collision: bool = True,
    ) -> str:
        local = self._build_local_part(user, rule.email_pattern)
        if not local:
            raise DirectoryModuleError("Unable to generate email local-part from template.", "email_template_invalid")
        base = f"{local}@{rule.domain}".lower()
        if not check_collision:
            return base

        exists_q = Q(primary_email__iexact=base)
        existing = DirectoryUser.objects.exclude(id=user.id).filter(exists_q).exists()
        if not existing and not ProvisioningRecord.objects.filter(generated_email__iexact=base).exists():
            return base

        if rule.collision_strategy == EmailCollisionStrategy.FAIL:
            raise DirectoryModuleError(f"Email collision for {base}.", "email_collision")

        counter = 1
        while True:
            candidate = f"{local}{counter}@{rule.domain}".lower()
            in_users = DirectoryUser.objects.exclude(id=user.id).filter(primary_email__iexact=candidate).exists()
            in_records = ProvisioningRecord.objects.filter(generated_email__iexact=candidate).exists()
            if not in_users and not in_records:
                return candidate
            counter += 1

    def resolve(self, user: DirectoryUser) -> ExpectedState:
        org_template = self.resolve_org_unit_template(user)
        email_rule = self.resolve_email_rule(user)
        expected_ou = org_template.target_org_unit_path if org_template else ""
        expected_email = ""
        if email_rule:
            expected_email = self.generate_expected_email(user, email_rule, check_collision=False)
        return ExpectedState(
            expected_org_unit_path=expected_ou,
            expected_email=expected_email,
            email_rule_id=email_rule.id if email_rule else None,
            org_template_id=org_template.id if org_template else None,
        )


class DirectorySyncService:
    def __init__(self, user):
        self.user = user
        self.directory = GoogleDirectoryService(user)

    def sync_users(
        self,
        query: str = "",
        max_results: Optional[int] = None,
        sync_job: Optional[DirectorySyncJob] = None,
    ) -> dict:
        now = timezone.now()
        created = 0
        updated = 0
        pages_fetched = 0
        users_fetched_total = 0

        if sync_job:
            sync_job.status = DirectorySyncJobStatus.RUNNING
            sync_job.started_at = sync_job.started_at or now
            sync_job.error_message = ""
            sync_job.save(update_fields=["status", "started_at", "error_message", "updated_at"])

        try:
            for batch in self.directory.iter_user_pages(query=query, max_results=max_results):
                pages_fetched += 1
                users_fetched_total += len(batch)

                for item in batch:
                    name = item.get("name") or {}
                    org_path = item.get("orgUnitPath", "") or ""
                    ext_ids = item.get("externalIds") or []
                    external_identifier = ""
                    for ext in ext_ids:
                        if ext.get("value"):
                            external_identifier = str(ext["value"]).strip()
                            break

                    primary_email = normalize_email(item.get("primaryEmail", ""))
                    full_name = (
                        item.get("name", {}).get("fullName", "")
                        or item.get("name", {}).get("givenName", "")
                    )
                    aliases = [
                        normalized
                        for normalized in (
                            normalize_email(alias) for alias in (item.get("aliases", []) or [])
                        )
                        if normalized
                    ]
                    phones = []
                    for raw_phone in item.get("phones", []) or []:
                        value = raw_phone.get("value") if isinstance(raw_phone, dict) else raw_phone
                        normalized_phone = normalize_phone(str(value or ""))
                        if normalized_phone:
                            phones.append(normalized_phone)

                    defaults = {
                        "primary_email": primary_email,
                        "full_name": full_name,
                        "given_name": name.get("givenName", ""),
                        "family_name": name.get("familyName", ""),
                        "org_unit_path": org_path,
                        "suspended": bool(item.get("suspended", False)),
                        "archived": bool(item.get("archived", False)),
                        "external_identifier": external_identifier,
                        "aliases_json": aliases,
                        "phones_json": phones,
                        "normalized_email": primary_email,
                        "normalized_full_name": normalize_name(full_name),
                        "normalized_phone": phones[0] if phones else "",
                        "is_active": not bool(item.get("suspended", False)) and not bool(item.get("archived", False)),
                        "last_seen_at": now,
                        "metadata_json": {
                            "aliases": item.get("aliases", []),
                            "nonEditableAliases": item.get("nonEditableAliases", []),
                            "isAdmin": item.get("isAdmin", False),
                            "isDelegatedAdmin": item.get("isDelegatedAdmin", False),
                        },
                        "raw_payload_json": item,
                        "sync_source": "google_directory",
                        "last_synced_at": now,
                    }
                    _, was_created = DirectoryUser.objects.update_or_create(
                        google_user_id=item.get("id", ""),
                        defaults=defaults,
                    )
                    created += int(was_created)
                    updated += int(not was_created)

                if sync_job:
                    sync_job.pages_fetched = pages_fetched
                    sync_job.users_fetched_total = users_fetched_total
                    sync_job.users_upserted_total = created + updated
                    sync_job.users_created_total = created
                    sync_job.users_updated_total = updated
                    sync_job.save(
                        update_fields=[
                            "pages_fetched",
                            "users_fetched_total",
                            "users_upserted_total",
                            "users_created_total",
                            "users_updated_total",
                            "updated_at",
                        ]
                    )

            total_directory_users = DirectoryUser.objects.count()
            result = {
                "synced": users_fetched_total,
                "created": created,
                "updated": updated,
                "pages_fetched": pages_fetched,
                "users_upserted_total": created + updated,
                "total_directory_users": total_directory_users,
                "timestamp": timezone.now().isoformat(),
            }
            if sync_job:
                sync_job.status = DirectorySyncJobStatus.COMPLETED
                sync_job.completed_at = timezone.now()
                sync_job.result_summary_json = result
                sync_job.save(
                    update_fields=[
                        "status",
                        "completed_at",
                        "result_summary_json",
                        "updated_at",
                    ]
                )
                result["sync_job_id"] = sync_job.id
            return result
        except Exception as exc:
            if sync_job:
                sync_job.status = DirectorySyncJobStatus.FAILED
                sync_job.completed_at = timezone.now()
                sync_job.error_message = str(exc)
                sync_job.save(
                    update_fields=[
                        "status",
                        "completed_at",
                        "error_message",
                        "updated_at",
                    ]
                )
            raise


class InconsistencyDetectionService:
    def __init__(self):
        self.resolver = ExpectedStateResolver()

    def _create_issue(
        self,
        user: DirectoryUser,
        issue_type: str,
        severity: str,
        actual: str,
        expected: str,
        action: str,
        metadata: Optional[dict] = None,
    ):
        DirectoryIssue.objects.create(
            directory_user=user,
            issue_type=issue_type,
            severity=severity,
            actual_value=actual,
            expected_value=expected,
            suggested_action=action,
            status=DirectoryIssueStatus.DETECTED,
            metadata_json=metadata or {},
        )

    @transaction.atomic
    def scan(self, users: Optional[Iterable[DirectoryUser]] = None) -> dict:
        qs = users if users is not None else DirectoryUser.objects.all()
        if not hasattr(qs, "values_list"):
            user_ids = [u.id for u in qs]
            qs = DirectoryUser.objects.filter(id__in=user_ids)
        else:
            user_ids = list(qs.values_list("id", flat=True))

        DirectoryIssue.objects.filter(
            directory_user_id__in=user_ids,
            status=DirectoryIssueStatus.DETECTED,
        ).delete()

        dup_identifiers = (
            DirectoryUser.objects.exclude(external_identifier="")
            .values("external_identifier")
            .annotate(n=Count("id"))
            .filter(n__gt=1)
        )
        duplicate_values = {row["external_identifier"] for row in dup_identifiers}

        issue_count = 0
        for user in qs:
            expected = self.resolver.resolve(user)
            user.expected_org_unit_path = expected.expected_org_unit_path
            if expected.expected_email:
                user.expected_email_valid = user.primary_email.lower() == expected.expected_email.lower()
            else:
                user.expected_email_valid = None
            user.save(update_fields=["expected_org_unit_path", "expected_email_valid", "updated_at"])

            if not expected.org_template_id:
                self._create_issue(
                    user,
                    DirectoryIssueType.TEMPLATE_RESOLUTION_FAILURE,
                    IssueSeverity.INFO,
                    actual=user.org_unit_path,
                    expected="org unit template required",
                    action="review_template",
                )
                issue_count += 1
            elif expected.expected_org_unit_path and user.org_unit_path != expected.expected_org_unit_path:
                self._create_issue(
                    user,
                    DirectoryIssueType.INVALID_ORG_UNIT,
                    IssueSeverity.WARNING,
                    actual=user.org_unit_path,
                    expected=expected.expected_org_unit_path,
                    action="move_ou",
                )
                issue_count += 1

            if not expected.email_rule_id:
                self._create_issue(
                    user,
                    DirectoryIssueType.TEMPLATE_RESOLUTION_FAILURE,
                    IssueSeverity.INFO,
                    actual=user.primary_email,
                    expected="email template rule required",
                    action="review_email_template",
                )
                issue_count += 1
            elif expected.expected_email and user.primary_email.lower() != expected.expected_email.lower():
                self._create_issue(
                    user,
                    DirectoryIssueType.INVALID_EMAIL_PATTERN,
                    IssueSeverity.WARNING,
                    actual=user.primary_email,
                    expected=expected.expected_email,
                    action="manual_review",
                )
                issue_count += 1

            if not (user.external_identifier or user.roll_number or user.employee_id):
                self._create_issue(
                    user,
                    DirectoryIssueType.MISSING_REQUIRED_IDENTIFIER,
                    IssueSeverity.WARNING,
                    actual="",
                    expected="identifier required",
                    action="update_identifier",
                )
                issue_count += 1

            if user.external_identifier and user.external_identifier in duplicate_values:
                self._create_issue(
                    user,
                    DirectoryIssueType.LIKELY_DUPLICATE_CONFLICT,
                    IssueSeverity.CRITICAL,
                    actual=user.external_identifier,
                    expected="unique identifier",
                    action="manual_review",
                )
                issue_count += 1

        return {"users_scanned": len(user_ids), "issues_created": issue_count}


class DirectoryChangeService:
    def __init__(self, user):
        self.user = user
        self.directory = GoogleDirectoryService(user)

    @transaction.atomic
    def build_preview_job(
        self,
        *,
        job_type: str,
        scope_type: str,
        issue_ids: list[int],
        user_ids: list[int],
        target_org_unit_path: str,
        input_payload: dict,
    ) -> DirectoryChangeJob:
        issues = DirectoryIssue.objects.filter(id__in=issue_ids) if issue_ids else DirectoryIssue.objects.none()
        users = DirectoryUser.objects.filter(id__in=user_ids) if user_ids else DirectoryUser.objects.none()
        if not issue_ids and not user_ids:
            raise DirectoryModuleError("Provide issue_ids or user_ids for preview.", "preview_empty_scope")

        requires_admin = scope_type == "bulk" or issues.filter(severity=IssueSeverity.CRITICAL).exists()
        preview_job = DirectoryChangeJob.objects.create(
            job_type=job_type,
            scope_type=scope_type,
            initiated_by=self.user,
            is_dry_run=True,
            requires_admin_approval=requires_admin,
            input_payload=input_payload or {},
            status=DirectoryChangeJobStatus.PREVIEW_READY,
        )

        created_items = 0
        for issue in issues.select_related("directory_user"):
            user = issue.directory_user
            if not user:
                continue
            action = "move_ou" if issue.issue_type == DirectoryIssueType.INVALID_ORG_UNIT else "unsupported"
            DirectoryChangeJobItem.objects.create(
                job=preview_job,
                directory_user=user,
                issue=issue,
                target_ref=user.primary_email,
                action=action,
                before_value=issue.actual_value or user.org_unit_path,
                after_value=issue.expected_value,
                payload_json={
                    "issue_id": issue.id,
                    "target_org_unit_path": issue.expected_value or target_org_unit_path,
                },
            )
            created_items += 1

        if not issue_ids:
            for user in users:
                if not target_org_unit_path:
                    raise DirectoryModuleError(
                        "target_org_unit_path is required for user-based OU correction preview.",
                        "target_ou_required",
                    )
                DirectoryChangeJobItem.objects.create(
                    job=preview_job,
                    directory_user=user,
                    target_ref=user.primary_email,
                    action="move_ou",
                    before_value=user.org_unit_path,
                    after_value=target_org_unit_path,
                    payload_json={"target_org_unit_path": target_org_unit_path},
                )
                created_items += 1

        preview_job.preview_summary = {
            "item_count": created_items,
            "requires_admin_approval": requires_admin,
            "non_mutating": True,
        }
        preview_job.save(update_fields=["preview_summary", "updated_at"])
        return preview_job

    @transaction.atomic
    def execute_from_preview(
        self,
        preview_job: DirectoryChangeJob,
        dry_run: bool = False,
        execute_now: bool = True,
        approval_request: Optional[ApprovalRequest] = None,
    ) -> DirectoryChangeJob:
        if preview_job.status != DirectoryChangeJobStatus.PREVIEW_READY:
            raise DirectoryModuleError("Preview job is not in preview_ready state.", "preview_invalid_state")
        if preview_job.scope_type == "bulk" and not preview_job.is_dry_run:
            raise DirectoryModuleError("Bulk execution must start from preview artifact.", "preview_required")
        if preview_job.requires_admin_approval and not dry_run and approval_request is None:
            raise DirectoryModuleError("Approved approval request is required for this execution.", "approval_required")

        input_payload = dict(preview_job.input_payload or {})
        if approval_request:
            input_payload["_approval_request_id"] = approval_request.id

        execution_job = DirectoryChangeJob.objects.create(
            job_type=preview_job.job_type,
            scope_type=preview_job.scope_type,
            initiated_by=self.user,
            approved_by=approval_request.reviewed_by if approval_request else (self.user if self.user.is_admin_role else None),
            approved_at=approval_request.reviewed_at if approval_request else (timezone.now() if self.user.is_admin_role else None),
            preview_of=preview_job,
            is_dry_run=dry_run,
            requires_admin_approval=preview_job.requires_admin_approval,
            input_payload=input_payload,
            status=DirectoryChangeJobStatus.RUNNING if execute_now else DirectoryChangeJobStatus.APPROVED,
            started_at=timezone.now() if execute_now else None,
        )

        for item in preview_job.items.all():
            DirectoryChangeJobItem.objects.create(
                job=execution_job,
                directory_user=item.directory_user,
                issue=item.issue,
                target_ref=item.target_ref,
                action=item.action,
                before_value=item.before_value,
                after_value=item.after_value,
                payload_json=item.payload_json,
            )

        if not execute_now:
            execution_job.execution_summary = {"queued": True}
            execution_job.save(update_fields=["execution_summary", "updated_at"])
            if approval_request:
                approval_request.execution_status = ApprovalExecutionStatus.READY_TO_EXECUTE
                approval_request.execution_message = "Execution queued."
                approval_request.save(update_fields=["execution_status", "execution_message", "updated_at"])
            return execution_job

        return self.execute_existing_job(execution_job, approval_request=approval_request)

    def execute_existing_job(
        self,
        execution_job: DirectoryChangeJob,
        approval_request: Optional[ApprovalRequest] = None,
    ) -> DirectoryChangeJob:
        if execution_job.status not in {
            DirectoryChangeJobStatus.APPROVED,
            DirectoryChangeJobStatus.RUNNING,
            DirectoryChangeJobStatus.PENDING,
        }:
            raise DirectoryModuleError("Change job is not executable in current state.", "job_not_executable")

        if approval_request is None:
            approval_request_id = (execution_job.input_payload or {}).get("_approval_request_id")
            if approval_request_id:
                approval_request = ApprovalRequest.objects.filter(id=approval_request_id).first()

        execution_job.status = DirectoryChangeJobStatus.RUNNING
        if not execution_job.started_at:
            execution_job.started_at = timezone.now()
        execution_job.save(update_fields=["status", "started_at", "updated_at"])

        dry_run = execution_job.is_dry_run
        success = skipped = failed = 0
        for item in execution_job.items.select_related("directory_user", "issue"):
            if item.action != "move_ou":
                item.status = ItemStatus.SKIPPED
                item.error_text = "Unsupported action in v1."
                item.save(update_fields=["status", "error_text", "updated_at"])
                skipped += 1
                continue

            user = item.directory_user
            if not user:
                item.status = ItemStatus.FAILED
                item.error_text = "Directory user missing."
                item.save(update_fields=["status", "error_text", "updated_at"])
                failed += 1
                continue

            target_ou = (item.payload_json or {}).get("target_org_unit_path") or item.after_value
            correlation_id = f"dir-change-{execution_job.id}-{item.id}"

            if dry_run:
                item.status = ItemStatus.SKIPPED
                item.result_json = {"dry_run": True, "target_org_unit_path": target_ou}
                item.save(update_fields=["status", "result_json", "updated_at"])
                DirectoryAuditService.log(
                    actor=self.user,
                    action_type="move_ou",
                    target_type="user",
                    target_ref=user.primary_email,
                    is_dry_run=True,
                    success=True,
                    before_json={"org_unit_path": user.org_unit_path},
                    after_json={"org_unit_path": target_ou},
                    request_json={"target_org_unit_path": target_ou},
                    response_json={"dry_run": True},
                    correlation_id=correlation_id,
                    approval_request=approval_request,
                    linked_change_job=execution_job,
                )
                skipped += 1
                continue

            try:
                result = self.directory.move_user_to_org_unit(user.primary_email, target_ou)
                old_ou = user.org_unit_path
                user.org_unit_path = target_ou
                user.save(update_fields=["org_unit_path", "updated_at"])
                item.status = ItemStatus.SUCCESS
                item.result_json = result
                item.save(update_fields=["status", "result_json", "updated_at"])
                DirectoryAuditService.log(
                    actor=self.user,
                    action_type="move_ou",
                    target_type="user",
                    target_ref=user.primary_email,
                    is_dry_run=False,
                    success=True,
                    before_json={"org_unit_path": old_ou},
                    after_json={"org_unit_path": target_ou},
                    request_json={"target_org_unit_path": target_ou},
                    response_json=result,
                    external_reference=result.get("user", {}).get("id", ""),
                    correlation_id=correlation_id,
                    approval_request=approval_request,
                    linked_change_job=execution_job,
                )
                if item.issue:
                    item.issue.status = DirectoryIssueStatus.APPLIED
                    item.issue.applied_at = timezone.now()
                    item.issue.failure_reason = ""
                    item.issue.save(update_fields=["status", "applied_at", "failure_reason", "updated_at"])
                success += 1
            except DirectoryServiceError as exc:
                item.status = ItemStatus.FAILED
                item.error_text = str(exc)
                item.result_json = {"error": str(exc), "code": exc.code}
                item.save(update_fields=["status", "error_text", "result_json", "updated_at"])
                DirectoryAuditService.log(
                    actor=self.user,
                    action_type="move_ou",
                    target_type="user",
                    target_ref=user.primary_email,
                    is_dry_run=False,
                    success=False,
                    before_json={"org_unit_path": user.org_unit_path},
                    after_json={"org_unit_path": target_ou},
                    request_json={"target_org_unit_path": target_ou},
                    response_json={"error": str(exc), "code": exc.code},
                    error_message=str(exc),
                    correlation_id=correlation_id,
                    approval_request=approval_request,
                    linked_change_job=execution_job,
                )
                if item.issue:
                    item.issue.status = DirectoryIssueStatus.FAILED
                    item.issue.failure_reason = str(exc)
                    item.issue.save(update_fields=["status", "failure_reason", "updated_at"])
                failed += 1

        execution_job.finished_at = timezone.now()
        if failed > 0 and success == 0:
            execution_job.status = DirectoryChangeJobStatus.FAILED
        elif failed > 0:
            execution_job.status = DirectoryChangeJobStatus.PARTIAL
        else:
            execution_job.status = DirectoryChangeJobStatus.COMPLETED
        execution_job.execution_summary = {
            "total": execution_job.items.count(),
            "success": success,
            "failed": failed,
            "skipped": skipped,
            "dry_run": dry_run,
        }
        execution_job.save(update_fields=["status", "execution_summary", "finished_at", "updated_at"])
        if approval_request and not dry_run:
            if execution_job.status == DirectoryChangeJobStatus.COMPLETED:
                approval_request.status = ApprovalRequestStatus.EXECUTED
                approval_request.execution_status = ApprovalExecutionStatus.EXECUTED
                approval_request.execution_message = "Linked execution completed."
            else:
                approval_request.status = ApprovalRequestStatus.EXECUTION_FAILED
                approval_request.execution_status = ApprovalExecutionStatus.EXECUTION_FAILED
                approval_request.execution_message = execution_job.failure_reason or "Linked execution reported failures."
            approval_request.save(update_fields=["status", "execution_status", "execution_message", "updated_at"])
        return execution_job


class ProvisioningService:
    def __init__(self, user):
        self.user = user
        self.resolver = ExpectedStateResolver()
        self.directory = GoogleDirectoryService(user)

    def _resolve_generated_email(
        self,
        *,
        user_category: str,
        full_name: str,
        given_name: str,
        family_name: str,
        source_identifier: str,
        department: str = "",
        program: str = "",
        batch: str = "",
        year: str = "",
        exclude_record_id: Optional[int] = None,
    ) -> tuple[str, str]:
        shadow = DirectoryUser(
            primary_email="",
            google_user_id="shadow",
            user_category=user_category,
            full_name=full_name,
            given_name=given_name,
            family_name=family_name,
            external_identifier=source_identifier,
            roll_number=source_identifier,
            department=department,
            program=program,
            batch=batch,
            year=year,
        )
        rule = self.resolver.resolve_email_rule(shadow)
        if not rule:
            raise DirectoryModuleError("No active email template rule matches this request.", "email_rule_missing")
        candidate = self.resolver.generate_expected_email(shadow, rule, check_collision=False)
        if not DirectoryUser.objects.filter(primary_email__iexact=candidate).exists():
            if exclude_record_id:
                existing = ProvisioningRecord.objects.exclude(id=exclude_record_id).filter(generated_email__iexact=candidate)
            else:
                existing = ProvisioningRecord.objects.filter(generated_email__iexact=candidate)
            if not existing.exists():
                return candidate, rule.domain

        if rule.collision_strategy == EmailCollisionStrategy.FAIL:
            raise DirectoryModuleError(f"Email collision detected for {candidate}.", "email_collision")

        local, _, domain = candidate.partition("@")
        index = 1
        while True:
            next_candidate = f"{local}{index}@{domain}"
            in_users = DirectoryUser.objects.filter(primary_email__iexact=next_candidate).exists()
            if exclude_record_id:
                in_records = ProvisioningRecord.objects.exclude(id=exclude_record_id).filter(
                    generated_email__iexact=next_candidate
                ).exists()
            else:
                in_records = ProvisioningRecord.objects.filter(generated_email__iexact=next_candidate).exists()
            if not in_users and not in_records:
                return next_candidate, domain
            index += 1

    def _resolve_target_ou(self, shadow_user: DirectoryUser) -> str:
        template = self.resolver.resolve_org_unit_template(shadow_user)
        if not template:
            raise DirectoryModuleError("No active OU template matches this request.", "ou_template_missing")
        return template.target_org_unit_path

    @transaction.atomic
    def preview_single(self, payload: dict, mode: str = ProvisioningMode.SINGLE) -> ProvisioningRecord:
        full_name = payload.get("full_name", "").strip()
        if not full_name:
            raise DirectoryModuleError("full_name is required.", "full_name_required")

        given_name = (payload.get("given_name") or "").strip()
        family_name = (payload.get("family_name") or "").strip()
        if not given_name and not family_name:
            given_name, family_name = _split_name(full_name)

        user_category = payload.get("user_category", "other")
        source_identifier = (payload.get("source_identifier") or "").strip()
        department = (payload.get("department") or "").strip()
        program = (payload.get("program") or "").strip()
        batch = (payload.get("batch") or "").strip()
        year = (payload.get("year") or "").strip()
        temp_password_policy = (payload.get("temp_password_policy") or "change_on_first_login").strip()

        generated_email, domain = self._resolve_generated_email(
            user_category=user_category,
            full_name=full_name,
            given_name=given_name,
            family_name=family_name,
            source_identifier=source_identifier,
            department=department,
            program=program,
            batch=batch,
            year=year,
        )

        shadow = DirectoryUser(
            primary_email=generated_email,
            google_user_id="shadow",
            full_name=full_name,
            given_name=given_name,
            family_name=family_name,
            user_category=user_category,
            external_identifier=source_identifier,
            roll_number=source_identifier,
            department=department,
            program=program,
            batch=batch,
            year=year,
        )
        target_ou = self._resolve_target_ou(shadow)
        preview_payload = {
            "full_name": full_name,
            "given_name": given_name,
            "family_name": family_name,
            "generated_email": generated_email,
            "domain": domain,
            "target_org_unit_path": target_ou,
            "temp_password_policy": temp_password_policy,
            "context": {
                "department": department,
                "program": program,
                "batch": batch,
                "year": year,
            },
        }
        return ProvisioningRecord.objects.create(
            full_name=full_name,
            given_name=given_name,
            family_name=family_name,
            user_category=user_category,
            source_identifier=source_identifier,
            generated_email=generated_email,
            target_org_unit_path=target_ou,
            temp_password_policy=temp_password_policy,
            provisioning_mode=mode,
            status=ProvisioningStatus.PREVIEWED,
            preview_payload=preview_payload,
            created_by=self.user,
        )

    @transaction.atomic
    def execute_record(
        self,
        record: ProvisioningRecord,
        dry_run: bool = False,
        approval_request: Optional[ApprovalRequest] = None,
    ) -> ProvisioningRecord:
        if record.status not in {ProvisioningStatus.PREVIEWED, ProvisioningStatus.APPROVED}:
            raise DirectoryModuleError("Provisioning record must be in previewed or approved status.", "invalid_status")

        correlation_id = f"provision-{record.id}"
        temp_password = secrets.token_urlsafe(12)
        request_payload = {
            "primary_email": record.generated_email,
            "given_name": record.given_name or record.full_name.split(" ")[0],
            "family_name": record.family_name or "User",
            "org_unit_path": record.target_org_unit_path,
            "password_policy": record.temp_password_policy,
        }

        if dry_run:
            record.status = ProvisioningStatus.PREVIEWED
            record.execution_payload = {"dry_run": True, "request": request_payload}
            record.save(update_fields=["status", "execution_payload", "updated_at"])
            DirectoryAuditService.log(
                actor=self.user,
                action_type="create_user",
                target_type="user",
                target_ref=record.generated_email,
                is_dry_run=True,
                success=True,
                request_json=request_payload,
                response_json={"dry_run": True},
                correlation_id=correlation_id,
                approval_request=approval_request,
                linked_provisioning_record=record,
            )
            return record

        try:
            result = self.directory.create_user(
                primary_email=record.generated_email,
                given_name=request_payload["given_name"],
                family_name=request_payload["family_name"],
                password=temp_password,
                org_unit_path=record.target_org_unit_path,
                change_password_at_next_login=True,
            )
            user_data = result.get("user", {})
            DirectoryUser.objects.update_or_create(
                google_user_id=user_data.get("id", ""),
                defaults={
                    "primary_email": user_data.get("primaryEmail", record.generated_email).lower(),
                    "full_name": user_data.get("name", {}).get("fullName", record.full_name),
                    "given_name": user_data.get("name", {}).get("givenName", record.given_name),
                    "family_name": user_data.get("name", {}).get("familyName", record.family_name),
                    "org_unit_path": user_data.get("orgUnitPath", record.target_org_unit_path),
                    "user_category": record.user_category,
                    "external_identifier": record.source_identifier,
                    "roll_number": record.source_identifier,
                    "metadata_json": {},
                    "raw_payload_json": user_data,
                    "last_synced_at": timezone.now(),
                    "sync_source": "provisioning",
                },
            )
            record.google_user_id = user_data.get("id", "")
            record.status = ProvisioningStatus.EXECUTED
            record.failure_reason = ""
            record.execution_payload = {"request": request_payload, "result": result}
            record.save(update_fields=["google_user_id", "status", "failure_reason", "execution_payload", "updated_at"])
            DirectoryAuditService.log(
                actor=self.user,
                action_type="create_user",
                target_type="user",
                target_ref=record.generated_email,
                is_dry_run=False,
                success=True,
                request_json=request_payload,
                response_json=result,
                external_reference=record.google_user_id,
                correlation_id=correlation_id,
                approval_request=approval_request,
                linked_provisioning_record=record,
            )
            return record
        except DirectoryServiceError as exc:
            record.status = ProvisioningStatus.FAILED
            record.failure_reason = str(exc)
            record.execution_payload = {"request": request_payload, "error": str(exc), "code": exc.code}
            record.save(update_fields=["status", "failure_reason", "execution_payload", "updated_at"])
            DirectoryAuditService.log(
                actor=self.user,
                action_type="create_user",
                target_type="user",
                target_ref=record.generated_email,
                is_dry_run=False,
                success=False,
                request_json=request_payload,
                response_json={"error": str(exc), "code": exc.code},
                error_message=str(exc),
                correlation_id=correlation_id,
                approval_request=approval_request,
                linked_provisioning_record=record,
            )
            return record

from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .google_client import GoogleService
from .google_scopes import GoogleScopeMissingError
from .directory_serializers import (
    ApprovalRequestCreateSerializer,
    ApprovalRequestSerializer,
    ApprovalReviewSerializer,
    BulkIssueApproveSerializer,
    BulkProvisioningCreateRequestSerializer,
    BulkProvisioningPreviewRequestSerializer,
    ChangeJobExecuteRequestSerializer,
    ChangeJobPreviewRequestSerializer,
    DirectoryAuditLogSerializer,
    DirectoryChangeJobSerializer,
    DirectoryIssueSerializer,
    DirectorySyncJobSerializer,
    DirectorySyncRequestSerializer,
    DirectoryUserSerializer,
    DirectoryUserUpdateSerializer,
    DirectoryVerifyJobSerializer,
    DirectoryVerifyRowSerializer,
    EmailTemplateRuleSerializer,
    IssueActionSerializer,
    IssueScanRequestSerializer,
    OrgUnitTemplateSerializer,
    ProvisioningCreateRequestSerializer,
    ProvisioningPreviewRequestSerializer,
    ProvisioningRecordSerializer,
)
from .models import (
    ApprovalActionType,
    ApprovalRequest,
    ApprovalRequestStatus,
    DirectoryAuditLog,
    DirectoryChangeJob,
    DirectoryIssue,
    DirectoryIssueStatus,
    DirectorySyncJob,
    DirectorySyncJobStatus,
    DirectoryUser,
    DirectoryVerifyJob,
    DirectoryVerifyJobStatus,
    DirectoryVerifyRow,
    EmailTemplateRule,
    OrgUnitTemplate,
    ProvisioningMode,
    ProvisioningRecord,
)
from .permissions import IsAdminOrStaff, IsOperatorOrAdmin
from .services.directory_module_service import (
    ApprovalService,
    DirectoryChangeService,
    DirectoryModuleError,
    DirectorySyncService,
    InconsistencyDetectionService,
    ProvisioningService,
)
from .services.directory_verification_service import (
    DirectoryVerificationError,
    DirectoryVerificationService,
    build_export_records,
    export_records_csv,
    export_records_xlsx,
    parse_mapping,
    parse_tabular_file,
    suggest_mapping,
)
from .services.google_directory_service import DirectoryServiceError
from .tasks import (
    directory_issue_scan_task,
    directory_sync_task,
    execute_directory_change_job_task,
    execute_provisioning_records_task,
)


def _scope_missing_response(exc: GoogleScopeMissingError):
    from urllib.parse import quote

    feature = exc.feature or ""
    upgrade_query = f"&upgrade={quote(feature)}" if feature else ""
    return Response(
        exc.as_payload(reauthorize_url=f"/api/auth/google/start?mode=upgrade{upgrade_query}"),
        status=403,
    )


def _is_admin(user) -> bool:
    return bool(getattr(user, "is_admin_role", False))


def _get_approval_request_or_404(approval_request_id: int):
    try:
        return ApprovalRequest.objects.select_related(
            "requested_by",
            "reviewed_by",
            "linked_change_job",
            "linked_provisioning_record",
        ).get(id=approval_request_id)
    except ApprovalRequest.DoesNotExist:
        return None


@api_view(["GET"])
@permission_classes([IsOperatorOrAdmin])
def list_directory_users(request):
    qs = DirectoryUser.objects.all()
    q = (request.query_params.get("q") or "").strip()
    category = (request.query_params.get("category") or "").strip()
    org_unit = (request.query_params.get("org_unit") or "").strip()
    issue_status = (request.query_params.get("issue_status") or "").strip()

    if q:
        qs = qs.filter(
            Q(primary_email__icontains=q)
            | Q(full_name__icontains=q)
            | Q(external_identifier__icontains=q)
            | Q(roll_number__icontains=q)
            | Q(employee_id__icontains=q)
        )
    if category:
        qs = qs.filter(user_category=category)
    if org_unit:
        qs = qs.filter(org_unit_path__icontains=org_unit)
    if issue_status:
        qs = qs.filter(issues__status=issue_status).distinct()

    return Response(DirectoryUserSerializer(qs.order_by("primary_email"), many=True).data)


@api_view(["GET", "PATCH"])
@permission_classes([IsOperatorOrAdmin])
def directory_user_detail(request, user_id: int):
    try:
        user = DirectoryUser.objects.get(id=user_id)
    except DirectoryUser.DoesNotExist:
        return Response({"detail": "Directory user not found."}, status=404)

    if request.method == "GET":
        return Response(DirectoryUserSerializer(user).data)

    ser = DirectoryUserUpdateSerializer(user, data=request.data, partial=True)
    if not ser.is_valid():
        return Response(ser.errors, status=400)
    ser.save()
    return Response(DirectoryUserSerializer(user).data)


@api_view(["POST"])
@permission_classes([IsOperatorOrAdmin])
def directory_sync(request):
    ser = DirectorySyncRequestSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=400)
    max_results = ser.validated_data.get("max_results")
    async_mode = bool(request.data.get("async", False))
    sync_job = DirectorySyncJob.objects.create(
        started_by=request.user,
        status=DirectorySyncJobStatus.QUEUED,
        query=ser.validated_data["query"],
        max_results=max_results,
    )

    if async_mode:
        task = directory_sync_task.delay(request.user.id, ser.validated_data["query"], max_results, sync_job.id)
        return Response(
            {
                "queued": True,
                "task_id": task.id,
                "sync_job": DirectorySyncJobSerializer(sync_job).data,
            },
            status=202,
        )

    service = DirectorySyncService(request.user)
    try:
        result = service.sync_users(
            query=ser.validated_data["query"],
            max_results=max_results,
            sync_job=sync_job,
        )
    except GoogleScopeMissingError as exc:
        return _scope_missing_response(exc)
    except (DirectoryModuleError, DirectoryServiceError) as exc:
        return Response({"detail": str(exc), "code": exc.code}, status=400)
    return Response(result)


@api_view(["GET"])
@permission_classes([IsOperatorOrAdmin])
def list_directory_sync_jobs(request):
    jobs = DirectorySyncJob.objects.select_related("started_by").order_by("-created_at")
    status_filter = (request.query_params.get("status") or "").strip()
    if status_filter:
        jobs = jobs.filter(status=status_filter)
    return Response(DirectorySyncJobSerializer(jobs[:100], many=True).data)


@api_view(["GET"])
@permission_classes([IsOperatorOrAdmin])
def get_directory_sync_job(request, job_id: int):
    try:
        job = DirectorySyncJob.objects.select_related("started_by").get(id=job_id)
    except DirectorySyncJob.DoesNotExist:
        return Response({"detail": "Sync job not found."}, status=404)
    return Response(DirectorySyncJobSerializer(job).data)


@api_view(["GET"])
@permission_classes([IsOperatorOrAdmin])
def directory_stats(request):
    total_users = DirectoryUser.objects.count()
    latest_job = DirectorySyncJob.objects.order_by("-created_at").first()
    running_job = (
        DirectorySyncJob.objects.filter(
            status__in=[DirectorySyncJobStatus.QUEUED, DirectorySyncJobStatus.RUNNING]
        )
        .order_by("-created_at")
        .first()
    )
    return Response(
        {
            "total_directory_users": total_users,
            "latest_sync_job": DirectorySyncJobSerializer(latest_job).data if latest_job else None,
            "running_sync_job": DirectorySyncJobSerializer(running_job).data if running_job else None,
        }
    )


@api_view(["GET"])
@permission_classes([IsOperatorOrAdmin])
def list_directory_issues(request):
    qs = DirectoryIssue.objects.select_related("directory_user", "reviewed_by").all()
    status_filter = (request.query_params.get("status") or "").strip()
    severity = (request.query_params.get("severity") or "").strip()
    issue_type = (request.query_params.get("issue_type") or "").strip()
    suggested_action = (request.query_params.get("suggested_action") or "").strip()
    q = (request.query_params.get("q") or "").strip()
    if status_filter:
        qs = qs.filter(status=status_filter)
    if severity:
        qs = qs.filter(severity=severity)
    if issue_type:
        qs = qs.filter(issue_type=issue_type)
    if suggested_action:
        qs = qs.filter(suggested_action=suggested_action)
    if q:
        qs = qs.filter(
            Q(directory_user__primary_email__icontains=q)
            | Q(actual_value__icontains=q)
            | Q(expected_value__icontains=q)
            | Q(issue_type__icontains=q)
            | Q(suggested_action__icontains=q)
            | Q(failure_reason__icontains=q)
        )
    return Response(DirectoryIssueSerializer(qs.order_by("-detected_at"), many=True).data)


@api_view(["GET"])
@permission_classes([IsOperatorOrAdmin])
def get_directory_issue(request, issue_id: int):
    try:
        issue = DirectoryIssue.objects.select_related("directory_user", "reviewed_by").get(id=issue_id)
    except DirectoryIssue.DoesNotExist:
        return Response({"detail": "Issue not found."}, status=404)
    return Response(DirectoryIssueSerializer(issue).data)


@api_view(["POST"])
@permission_classes([IsOperatorOrAdmin])
def scan_directory_issues(request):
    ser = IssueScanRequestSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=400)

    user_ids = ser.validated_data.get("user_ids", [])
    async_mode = bool(request.data.get("async", False))
    if async_mode:
        task = directory_issue_scan_task.delay(user_ids)
        return Response({"queued": True, "task_id": task.id}, status=202)

    users = DirectoryUser.objects.filter(id__in=user_ids) if user_ids else None
    result = InconsistencyDetectionService().scan(users=users)
    return Response(result)


def _transition_issue(request, issue_id: int, status_value: str):
    try:
        issue = DirectoryIssue.objects.get(id=issue_id)
    except DirectoryIssue.DoesNotExist:
        return Response({"detail": "Issue not found."}, status=404)
    ser = IssueActionSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=400)
    issue.status = status_value
    issue.reviewed_by = request.user
    issue.reviewed_at = timezone.now()
    issue.failure_reason = ser.validated_data["note"] if status_value == DirectoryIssueStatus.REJECTED else issue.failure_reason
    issue.save(update_fields=["status", "reviewed_by", "reviewed_at", "failure_reason", "updated_at"])
    return Response(DirectoryIssueSerializer(issue).data)


@api_view(["POST"])
@permission_classes([IsOperatorOrAdmin])
def approve_directory_issue(request, issue_id: int):
    return _transition_issue(request, issue_id, DirectoryIssueStatus.APPROVED)


@api_view(["POST"])
@permission_classes([IsOperatorOrAdmin])
def reject_directory_issue(request, issue_id: int):
    return _transition_issue(request, issue_id, DirectoryIssueStatus.REJECTED)


@api_view(["POST"])
@permission_classes([IsOperatorOrAdmin])
def mark_exception_directory_issue(request, issue_id: int):
    return _transition_issue(request, issue_id, DirectoryIssueStatus.EXCEPTION_MARKED)


@api_view(["POST"])
@permission_classes([IsOperatorOrAdmin])
def bulk_approve_directory_issues(request):
    ser = BulkIssueApproveSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=400)
    qs = DirectoryIssue.objects.filter(id__in=ser.validated_data["issue_ids"])
    count = qs.update(
        status=DirectoryIssueStatus.APPROVED,
        reviewed_by=request.user,
        reviewed_at=timezone.now(),
        updated_at=timezone.now(),
    )
    return Response({"approved": count})


@api_view(["GET", "POST"])
@permission_classes([IsOperatorOrAdmin])
def org_unit_templates(request):
    if request.method == "GET":
        templates = OrgUnitTemplate.objects.all().order_by("priority", "id")
        return Response(OrgUnitTemplateSerializer(templates, many=True).data)
    if not _is_admin(request.user):
        return Response({"detail": "Admin role required to manage OU templates."}, status=403)
    ser = OrgUnitTemplateSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=400)
    ser.save()
    return Response(ser.data, status=201)


@api_view(["PATCH"])
@permission_classes([IsOperatorOrAdmin])
def org_unit_template_detail(request, template_id: int):
    if not _is_admin(request.user):
        return Response({"detail": "Admin role required to edit OU templates."}, status=403)
    try:
        template = OrgUnitTemplate.objects.get(id=template_id)
    except OrgUnitTemplate.DoesNotExist:
        return Response({"detail": "Template not found."}, status=404)
    ser = OrgUnitTemplateSerializer(template, data=request.data, partial=True)
    if not ser.is_valid():
        return Response(ser.errors, status=400)
    ser.save()
    return Response(ser.data)


@api_view(["GET", "POST"])
@permission_classes([IsOperatorOrAdmin])
def email_template_rules(request):
    if request.method == "GET":
        rules = EmailTemplateRule.objects.all().order_by("priority", "id")
        return Response(EmailTemplateRuleSerializer(rules, many=True).data)
    if not _is_admin(request.user):
        return Response({"detail": "Admin role required to manage email template rules."}, status=403)
    ser = EmailTemplateRuleSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=400)
    ser.save()
    return Response(ser.data, status=201)


@api_view(["PATCH"])
@permission_classes([IsOperatorOrAdmin])
def email_template_rule_detail(request, rule_id: int):
    if not _is_admin(request.user):
        return Response({"detail": "Admin role required to edit email template rules."}, status=403)
    try:
        rule = EmailTemplateRule.objects.get(id=rule_id)
    except EmailTemplateRule.DoesNotExist:
        return Response({"detail": "Rule not found."}, status=404)
    ser = EmailTemplateRuleSerializer(rule, data=request.data, partial=True)
    if not ser.is_valid():
        return Response(ser.errors, status=400)
    ser.save()
    return Response(ser.data)


@api_view(["POST"])
@permission_classes([IsOperatorOrAdmin])
def preview_directory_change_job(request):
    ser = ChangeJobPreviewRequestSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=400)
    service = DirectoryChangeService(request.user)
    try:
        job = service.build_preview_job(
            job_type=ser.validated_data["job_type"],
            scope_type=ser.validated_data["scope_type"],
            issue_ids=ser.validated_data.get("issue_ids", []),
            user_ids=ser.validated_data.get("user_ids", []),
            target_org_unit_path=ser.validated_data.get("target_org_unit_path", ""),
            input_payload=ser.validated_data.get("input_payload", {}),
        )
    except GoogleScopeMissingError as exc:
        return _scope_missing_response(exc)
    except DirectoryModuleError as exc:
        return Response({"detail": str(exc), "code": exc.code}, status=400)
    return Response(DirectoryChangeJobSerializer(job).data, status=201)


@api_view(["POST"])
@permission_classes([IsOperatorOrAdmin])
def execute_directory_change_job(request):
    ser = ChangeJobExecuteRequestSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=400)
    try:
        preview_job = DirectoryChangeJob.objects.get(id=ser.validated_data["preview_job_id"])
    except DirectoryChangeJob.DoesNotExist:
        return Response({"detail": "Preview job not found."}, status=404)

    approval_request = None
    if preview_job.scope_type == "bulk" and not ser.validated_data["dry_run"]:
        approval_request_id = ser.validated_data.get("approval_request_id")
        if not approval_request_id:
            return Response(
                {"detail": "approval_request_id is required for bulk change execution."},
                status=400,
            )
        approval_request = _get_approval_request_or_404(approval_request_id)
        if not approval_request:
            return Response({"detail": "Approval request not found."}, status=404)
        if approval_request.action_type != ApprovalActionType.BULK_CHANGE_JOB_EXECUTE:
            return Response({"detail": "Approval request action type mismatch for bulk change execution."}, status=400)
        if approval_request.linked_change_job_id != preview_job.id:
            return Response({"detail": "Approval request is not linked to this preview job."}, status=400)
        if approval_request.status != ApprovalRequestStatus.APPROVED:
            return Response({"detail": f"Approval request status is {approval_request.status}, expected approved."}, status=400)

    async_mode = bool(request.data.get("async", True))
    service = DirectoryChangeService(request.user)
    should_queue = async_mode and not ser.validated_data["dry_run"] and preview_job.items.count() > 20
    try:
        execution_job = service.execute_from_preview(
            preview_job,
            dry_run=ser.validated_data["dry_run"],
            execute_now=not should_queue,
            approval_request=approval_request,
        )
    except GoogleScopeMissingError as exc:
        return _scope_missing_response(exc)
    except DirectoryModuleError as exc:
        return Response({"detail": str(exc), "code": exc.code}, status=400)

    if should_queue:
        task = execute_directory_change_job_task.delay(execution_job.id)
        return Response(
            {"queued": True, "task_id": task.id, "job": DirectoryChangeJobSerializer(execution_job).data},
            status=202,
        )
    return Response(DirectoryChangeJobSerializer(execution_job).data)


@api_view(["GET"])
@permission_classes([IsOperatorOrAdmin])
def list_directory_change_jobs(request):
    jobs = DirectoryChangeJob.objects.select_related("initiated_by", "approved_by", "preview_of").order_by("-created_at")
    return Response(DirectoryChangeJobSerializer(jobs, many=True).data)


@api_view(["GET"])
@permission_classes([IsOperatorOrAdmin])
def get_directory_change_job(request, job_id: int):
    try:
        job = DirectoryChangeJob.objects.select_related("initiated_by", "approved_by", "preview_of").get(id=job_id)
    except DirectoryChangeJob.DoesNotExist:
        return Response({"detail": "Job not found."}, status=404)
    return Response(DirectoryChangeJobSerializer(job).data)


@api_view(["GET", "POST"])
@permission_classes([IsOperatorOrAdmin])
def directory_approval_requests(request):
    if request.method == "GET":
        qs = ApprovalRequest.objects.select_related(
            "requested_by",
            "reviewed_by",
            "linked_change_job",
            "linked_provisioning_record",
        ).order_by("-created_at")
        if not _is_admin(request.user):
            qs = qs.filter(requested_by=request.user)
        status_filter = (request.query_params.get("status") or "").strip()
        action_type = (request.query_params.get("action_type") or "").strip()
        if status_filter:
            qs = qs.filter(status=status_filter)
        if action_type:
            qs = qs.filter(action_type=action_type)
        return Response(ApprovalRequestSerializer(qs, many=True).data)

    ser = ApprovalRequestCreateSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=400)

    linked_change_job = None
    linked_provisioning_record = None
    linked_change_job_id = ser.validated_data.get("linked_change_job_id")
    if linked_change_job_id:
        try:
            linked_change_job = DirectoryChangeJob.objects.get(id=linked_change_job_id)
        except DirectoryChangeJob.DoesNotExist:
            return Response({"detail": "linked_change_job_id not found."}, status=404)
    linked_provisioning_record_id = ser.validated_data.get("linked_provisioning_record_id")
    if linked_provisioning_record_id:
        try:
            linked_provisioning_record = ProvisioningRecord.objects.get(id=linked_provisioning_record_id)
        except ProvisioningRecord.DoesNotExist:
            return Response({"detail": "linked_provisioning_record_id not found."}, status=404)

    action_type = ser.validated_data["action_type"]
    payload = ser.validated_data.get("payload", {})
    if action_type == ApprovalActionType.BULK_CHANGE_JOB_EXECUTE:
        if not linked_change_job:
            return Response({"detail": "linked_change_job_id is required for bulk change execution approval."}, status=400)
        if linked_change_job.scope_type != "bulk":
            return Response({"detail": "Approval action is only valid for bulk change jobs."}, status=400)
    if action_type == ApprovalActionType.BULK_PROVISIONING_CREATE:
        record_ids = payload.get("preview_record_ids", [])
        if not isinstance(record_ids, list) or not record_ids:
            return Response({"detail": "payload.preview_record_ids is required for bulk provisioning approval."}, status=400)

    approval = ApprovalService.create_request(
        requested_by=request.user,
        action_type=action_type,
        target_type=ser.validated_data["target_type"],
        target_reference=ser.validated_data["target_reference"],
        payload=payload,
        linked_change_job=linked_change_job,
        linked_provisioning_record=linked_provisioning_record,
    )
    return Response(ApprovalRequestSerializer(approval).data, status=201)


@api_view(["GET"])
@permission_classes([IsOperatorOrAdmin])
def directory_approval_request_detail(request, approval_request_id: int):
    approval = _get_approval_request_or_404(approval_request_id)
    if not approval:
        return Response({"detail": "Approval request not found."}, status=404)
    if not _is_admin(request.user) and approval.requested_by_id != request.user.id:
        return Response({"detail": "Not permitted to view this approval request."}, status=403)
    return Response(ApprovalRequestSerializer(approval).data)


@api_view(["POST"])
@permission_classes([IsAdminOrStaff])
def approve_directory_approval_request(request, approval_request_id: int):
    approval = _get_approval_request_or_404(approval_request_id)
    if not approval:
        return Response({"detail": "Approval request not found."}, status=404)
    ser = ApprovalReviewSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=400)
    try:
        approval = ApprovalService.approve(
            approval=approval,
            reviewer=request.user,
            review_notes=ser.validated_data["review_notes"],
        )
    except DirectoryModuleError as exc:
        return Response({"detail": str(exc), "code": exc.code}, status=400)
    return Response(ApprovalRequestSerializer(approval).data)


@api_view(["POST"])
@permission_classes([IsAdminOrStaff])
def reject_directory_approval_request(request, approval_request_id: int):
    approval = _get_approval_request_or_404(approval_request_id)
    if not approval:
        return Response({"detail": "Approval request not found."}, status=404)
    ser = ApprovalReviewSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=400)
    try:
        approval = ApprovalService.reject(
            approval=approval,
            reviewer=request.user,
            review_notes=ser.validated_data["review_notes"],
        )
    except DirectoryModuleError as exc:
        return Response({"detail": str(exc), "code": exc.code}, status=400)
    return Response(ApprovalRequestSerializer(approval).data)


@api_view(["POST"])
@permission_classes([IsOperatorOrAdmin])
def cancel_directory_approval_request(request, approval_request_id: int):
    approval = _get_approval_request_or_404(approval_request_id)
    if not approval:
        return Response({"detail": "Approval request not found."}, status=404)
    if not _is_admin(request.user) and approval.requested_by_id != request.user.id:
        return Response({"detail": "Only requester or admin can cancel this approval request."}, status=403)
    ser = ApprovalReviewSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=400)
    try:
        approval = ApprovalService.cancel(
            approval=approval,
            actor=request.user,
            review_notes=ser.validated_data["review_notes"],
        )
    except DirectoryModuleError as exc:
        return Response({"detail": str(exc), "code": exc.code}, status=400)
    return Response(ApprovalRequestSerializer(approval).data)


@api_view(["POST"])
@permission_classes([IsOperatorOrAdmin])
def provisioning_preview(request):
    ser = ProvisioningPreviewRequestSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=400)
    try:
        record = ProvisioningService(request.user).preview_single(ser.validated_data, mode=ProvisioningMode.SINGLE)
    except GoogleScopeMissingError as exc:
        return _scope_missing_response(exc)
    except DirectoryModuleError as exc:
        return Response({"detail": str(exc), "code": exc.code}, status=400)
    return Response(ProvisioningRecordSerializer(record).data, status=201)


@api_view(["POST"])
@permission_classes([IsOperatorOrAdmin])
def provisioning_create(request):
    ser = ProvisioningCreateRequestSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=400)
    service = ProvisioningService(request.user)
    preview_record_id = ser.validated_data.get("preview_record_id")
    if preview_record_id:
        try:
            record = ProvisioningRecord.objects.get(id=preview_record_id)
        except ProvisioningRecord.DoesNotExist:
            return Response({"detail": "Preview record not found."}, status=404)
    else:
        payload = ser.validated_data.get("payload")
        if not payload:
            return Response({"detail": "preview_record_id or payload is required."}, status=400)
        try:
            record = service.preview_single(payload, mode=ProvisioningMode.SINGLE)
        except GoogleScopeMissingError as exc:
            return _scope_missing_response(exc)
        except DirectoryModuleError as exc:
            return Response({"detail": str(exc), "code": exc.code}, status=400)
    try:
        result = service.execute_record(record, dry_run=bool(request.data.get("dry_run", False)))
    except GoogleScopeMissingError as exc:
        return _scope_missing_response(exc)
    except DirectoryModuleError as exc:
        return Response({"detail": str(exc), "code": exc.code}, status=400)
    return Response(ProvisioningRecordSerializer(result).data)


@api_view(["POST"])
@permission_classes([IsOperatorOrAdmin])
def provisioning_bulk_preview(request):
    ser = BulkProvisioningPreviewRequestSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=400)
    service = ProvisioningService(request.user)
    records = []
    errors = []
    for idx, row in enumerate(ser.validated_data["rows"], start=1):
        try:
            record = service.preview_single(row, mode=ProvisioningMode.BULK)
            records.append(ProvisioningRecordSerializer(record).data)
        except GoogleScopeMissingError as exc:
            return _scope_missing_response(exc)
        except DirectoryModuleError as exc:
            errors.append({"row": idx, "detail": str(exc), "code": exc.code})
    return Response({"records": records, "errors": errors, "preview_count": len(records), "error_count": len(errors)})


@api_view(["POST"])
@permission_classes([IsOperatorOrAdmin])
def provisioning_bulk_create(request):
    ser = BulkProvisioningCreateRequestSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=400)
    dry_run = bool(request.data.get("dry_run", False))

    approval_request = None
    if not dry_run:
        approval_request_id = ser.validated_data.get("approval_request_id")
        if not approval_request_id:
            return Response({"detail": "approval_request_id is required for bulk provisioning create."}, status=400)
        approval_request = _get_approval_request_or_404(approval_request_id)
        if not approval_request:
            return Response({"detail": "Approval request not found."}, status=404)
        if approval_request.action_type != ApprovalActionType.BULK_PROVISIONING_CREATE:
            return Response({"detail": "Approval request action type mismatch for bulk provisioning create."}, status=400)
        if approval_request.status != ApprovalRequestStatus.APPROVED:
            return Response({"detail": f"Approval request status is {approval_request.status}, expected approved."}, status=400)

    record_ids = ser.validated_data["preview_record_ids"]
    records = list(ProvisioningRecord.objects.filter(id__in=record_ids))
    if len(records) != len(record_ids):
        return Response({"detail": "One or more preview records were not found."}, status=404)
    if any(r.status not in {"previewed", "approved"} for r in records):
        return Response({"detail": "All records must be in previewed or approved status."}, status=400)
    if approval_request:
        approved_ids = sorted((approval_request.payload or {}).get("preview_record_ids", []))
        if sorted(record_ids) != approved_ids:
            return Response({"detail": "Approval request payload does not match selected provisioning records."}, status=400)

    try:
        GoogleService(request.user).require_feature_scope("create_directory_user")
    except GoogleScopeMissingError as exc:
        return _scope_missing_response(exc)

    task = execute_provisioning_records_task.delay(
        request.user.id,
        record_ids,
        dry_run,
        approval_request.id if approval_request else None,
    )
    return Response({"queued": True, "task_id": task.id, "record_count": len(record_ids)}, status=202)


@api_view(["GET"])
@permission_classes([IsOperatorOrAdmin])
def list_provisioning_records(request):
    records = ProvisioningRecord.objects.select_related("created_by", "approved_by", "change_job").order_by("-created_at")
    return Response(ProvisioningRecordSerializer(records, many=True).data)


@api_view(["GET"])
@permission_classes([IsOperatorOrAdmin])
def get_provisioning_record(request, record_id: int):
    try:
        record = ProvisioningRecord.objects.select_related("created_by", "approved_by", "change_job").get(id=record_id)
    except ProvisioningRecord.DoesNotExist:
        return Response({"detail": "Provisioning record not found."}, status=404)
    return Response(ProvisioningRecordSerializer(record).data)


@api_view(["GET"])
@permission_classes([IsOperatorOrAdmin])
def list_directory_audit_logs(request):
    logs = DirectoryAuditLog.objects.select_related("actor").order_by("-created_at")[:500]
    return Response(DirectoryAuditLogSerializer(logs, many=True).data)


@api_view(["GET"])
@permission_classes([IsOperatorOrAdmin])
def get_directory_audit_log(request, log_id: int):
    try:
        log = DirectoryAuditLog.objects.select_related("actor").get(id=log_id)
    except DirectoryAuditLog.DoesNotExist:
        return Response({"detail": "Audit log not found."}, status=404)
    return Response(DirectoryAuditLogSerializer(log).data)


@api_view(["POST"])
@permission_classes([IsOperatorOrAdmin])
def verify_upload_directory(request):
    uploaded = request.FILES.get("file")
    if uploaded is None:
        return Response({"detail": "file is required."}, status=400)

    sheet_name = (request.data.get("sheet_name") or "").strip()
    try:
        headers, rows, selected_sheet, available_sheets = parse_tabular_file(
            uploaded.name,
            uploaded.read(),
            sheet_name=sheet_name,
        )
    except DirectoryVerificationError as exc:
        return Response({"detail": str(exc), "code": exc.code}, status=400)

    mapping_raw = request.data.get("mapping")
    suggested = suggest_mapping(headers)
    if mapping_raw in (None, ""):
        return Response(
            {
                "requires_mapping": True,
                "source_filename": uploaded.name,
                "source_type": "xlsx" if uploaded.name.lower().endswith((".xlsx", ".xlsm")) else "csv",
                "sheet_name": selected_sheet,
                "available_sheets": available_sheets,
                "headers": headers,
                "suggested_mapping": suggested,
                "row_count": len(rows),
                "sample_rows": rows[:5],
            }
        )

    try:
        mapping = parse_mapping(mapping_raw)
    except DirectoryVerificationError as exc:
        return Response({"detail": str(exc), "code": exc.code}, status=400)

    mapped_headers = [h for h in mapping.values() if h]
    invalid_headers = [h for h in mapped_headers if h not in headers]
    if invalid_headers:
        return Response(
            {
                "detail": f"Mapping references unknown headers: {', '.join(invalid_headers)}",
                "code": "invalid_mapping_headers",
            },
            status=400,
        )

    has_any_email = any(mapping.get(k) for k in ["official_email_issued", "email_address", "email_pmc"])
    has_name_phone = bool(mapping.get("name") and mapping.get("phone_number"))
    has_name_roll = bool(mapping.get("name") and mapping.get("roll_no"))
    if not (has_any_email or has_name_phone or has_name_roll):
        return Response(
            {
                "detail": "Mapping must include at least one searchable combination (email, or name+phone, or name+roll_no).",
                "code": "insufficient_mapping",
            },
            status=400,
        )

    source_type = "xlsx" if uploaded.name.lower().endswith((".xlsx", ".xlsm")) else "csv"
    service = DirectoryVerificationService()
    try:
        job = service.run_job(
            created_by=request.user,
            source_filename=uploaded.name,
            source_type=source_type,
            sheet_name=selected_sheet,
            rows=rows,
            mapping=mapping,
        )
    except DirectoryVerificationError as exc:
        return Response({"detail": str(exc), "code": exc.code}, status=400)
    except Exception as exc:
        failed_job = DirectoryVerifyJob.objects.create(
            created_by=request.user,
            source_filename=uploaded.name,
            source_type=source_type,
            sheet_name=selected_sheet,
            row_count=len(rows),
            status=DirectoryVerifyJobStatus.FAILED,
            error_message=str(exc),
        )
        return Response(
            {
                "detail": "Verification processing failed.",
                "code": "verification_failed",
                "job": DirectoryVerifyJobSerializer(failed_job).data,
            },
            status=500,
        )

    return Response(DirectoryVerifyJobSerializer(job).data, status=201)


@api_view(["GET"])
@permission_classes([IsOperatorOrAdmin])
def list_directory_verify_jobs(request):
    jobs = DirectoryVerifyJob.objects.select_related("created_by").order_by("-created_at")
    status_filter = (request.query_params.get("status") or "").strip()
    if status_filter:
        jobs = jobs.filter(status=status_filter)
    return Response(DirectoryVerifyJobSerializer(jobs[:100], many=True).data)


@api_view(["GET"])
@permission_classes([IsOperatorOrAdmin])
def get_directory_verify_job(request, job_id: int):
    try:
        job = DirectoryVerifyJob.objects.select_related("created_by").get(id=job_id)
    except DirectoryVerifyJob.DoesNotExist:
        return Response({"detail": "Verification job not found."}, status=404)
    return Response(DirectoryVerifyJobSerializer(job).data)


@api_view(["GET"])
@permission_classes([IsOperatorOrAdmin])
def list_directory_verify_rows(request, job_id: int):
    try:
        DirectoryVerifyJob.objects.get(id=job_id)
    except DirectoryVerifyJob.DoesNotExist:
        return Response({"detail": "Verification job not found."}, status=404)

    verdict_filter = (request.query_params.get("verdict") or "").strip()
    page = max(int(request.query_params.get("page") or 1), 1)
    page_size = min(max(int(request.query_params.get("page_size") or 100), 1), 500)

    qs = DirectoryVerifyRow.objects.select_related("matched_directory_user").filter(job_id=job_id).order_by("row_no", "id")
    if verdict_filter:
        qs = qs.filter(verdict=verdict_filter)
    total = qs.count()
    start = (page - 1) * page_size
    end = start + page_size
    rows = qs[start:end]
    return Response(
        {
            "total": total,
            "page": page,
            "page_size": page_size,
            "results": DirectoryVerifyRowSerializer(rows, many=True).data,
        }
    )


@api_view(["GET"])
@permission_classes([IsOperatorOrAdmin])
def export_directory_verify_job(request, job_id: int):
    try:
        job = DirectoryVerifyJob.objects.get(id=job_id)
    except DirectoryVerifyJob.DoesNotExist:
        return Response({"detail": "Verification job not found."}, status=404)

    fmt = (
        request.query_params.get("file_format")
        or request.query_params.get("export_format")
        or "csv"
    ).strip().lower()
    rows = DirectoryVerifyRow.objects.select_related("matched_directory_user").filter(job=job).order_by("row_no", "id")
    records = build_export_records(rows)
    filename_base = f"directory-verify-job-{job.id}"

    if fmt == "xlsx":
        content = export_records_xlsx(records)
        response = HttpResponse(
            content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename_base}.xlsx"'
        return response

    if fmt != "csv":
        return Response({"detail": "Unsupported export format. Use csv or xlsx."}, status=400)

    content = export_records_csv(records)
    response = HttpResponse(content, content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename_base}.csv"'
    return response

"""Phase 2 — Admin Commands + Enrollment API views."""

import logging
import urllib.parse

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import ActionType, CommandJob, CommandJobItem, DirectoryTarget, ItemStatus, OnboardingBundle, TargetType
from .permissions import IsAdminOrStaff
from .google_scopes import GoogleScopeMissingError
from .serializers import (
    CommandJobItemSerializer,
    CommandJobListSerializer,
    CommandJobSerializer,
    DirectoryTargetSerializer,
    OnboardingBundleSerializer,
)
from .services.classroom_service import ClassroomRosterService, ClassroomServiceError
from .services.command_executor import CommandExecutor, CommandExecutorError
from .services.google_directory_service import DirectoryServiceError, GoogleDirectoryService
from .tasks import execute_command_job_task, retry_command_job_task

logger = logging.getLogger(__name__)


def _scope_missing_response(exc: GoogleScopeMissingError):
    feature = exc.feature or ""
    upgrade_query = f"&upgrade={urllib.parse.quote(feature)}" if feature else ""
    return Response(
        exc.as_payload(reauthorize_url=f"/api/auth/google/start?mode=upgrade{upgrade_query}"),
        status=403,
    )


# ---------------------------------------------------------------------------
# Groups API
# ---------------------------------------------------------------------------

@api_view(["GET"])
@permission_classes([IsAdminOrStaff])
def list_groups(request):
    """GET /api/groups — list synced groups from DirectoryTarget cache."""
    targets = DirectoryTarget.objects.filter(target_type=TargetType.GROUP).order_by("display_name")
    return Response(DirectoryTargetSerializer(targets, many=True).data)


@api_view(["POST"])
@permission_classes([IsAdminOrStaff])
def sync_groups(request):
    """POST /api/groups/sync — fetch groups from Google and upsert to DirectoryTarget."""
    service = GoogleDirectoryService(request.user)
    try:
        result = service.sync_groups_to_directory_targets(domain=request.data.get("domain"))
    except GoogleScopeMissingError as exc:
        return _scope_missing_response(exc)
    except DirectoryServiceError as exc:
        return Response({"detail": str(exc), "code": exc.code}, status=400)
    return Response(result)


@api_view(["POST"])
@permission_classes([IsAdminOrStaff])
def add_member_to_group(request):
    """POST /api/groups/add-member — add a user to a Google Group."""
    group_email = (request.data.get("group_email") or "").strip()
    user_email = (request.data.get("user_email") or "").strip()
    if not group_email or not user_email:
        return Response({"detail": "group_email and user_email are required."}, status=400)

    service = GoogleDirectoryService(request.user)
    try:
        result = service.add_member_to_group(group_email, user_email)
    except GoogleScopeMissingError as exc:
        return _scope_missing_response(exc)
    except DirectoryServiceError as exc:
        return Response({"detail": str(exc), "code": exc.code}, status=400)
    return Response(result)


@api_view(["POST"])
@permission_classes([IsAdminOrStaff])
def remove_member_from_group(request):
    """POST /api/groups/remove-member — remove a user from a Google Group."""
    group_email = (request.data.get("group_email") or "").strip()
    user_email = (request.data.get("user_email") or "").strip()
    if not group_email or not user_email:
        return Response({"detail": "group_email and user_email are required."}, status=400)

    service = GoogleDirectoryService(request.user)
    try:
        result = service.remove_member_from_group(group_email, user_email)
    except GoogleScopeMissingError as exc:
        return _scope_missing_response(exc)
    except DirectoryServiceError as exc:
        return Response({"detail": str(exc), "code": exc.code}, status=400)
    return Response(result)


@api_view(["GET"])
@permission_classes([IsAdminOrStaff])
def list_group_members(request, group_email):
    """GET /api/groups/{group_email}/members — list members of a Google Group."""
    service = GoogleDirectoryService(request.user)
    try:
        members = service.list_group_members(group_email)
    except GoogleScopeMissingError as exc:
        return _scope_missing_response(exc)
    except DirectoryServiceError as exc:
        return Response({"detail": str(exc), "code": exc.code}, status=400)
    return Response({"group_email": group_email, "members": members, "count": len(members)})


# ---------------------------------------------------------------------------
# Classroom Admin API
# ---------------------------------------------------------------------------

@api_view(["GET"])
@permission_classes([IsAdminOrStaff])
def list_classroom_courses(request):
    """GET /api/classroom/courses — list active Classroom courses."""
    service = ClassroomRosterService(request.user)
    try:
        courses = service.list_courses()
    except GoogleScopeMissingError as exc:
        return _scope_missing_response(exc)
    except ClassroomServiceError as exc:
        return Response({"detail": str(exc), "code": exc.code}, status=400)
    return Response({"courses": courses, "count": len(courses)})


@api_view(["GET"])
@permission_classes([IsAdminOrStaff])
def list_classroom_course_roster(request, course_id):
    """GET /api/classroom/courses/{course_id}/roster — list enrolled students and teachers."""
    service = ClassroomRosterService(request.user)
    try:
        students = service.list_students(course_id)
        teachers = service.list_teachers(course_id)
    except GoogleScopeMissingError as exc:
        return _scope_missing_response(exc)
    except ClassroomServiceError as exc:
        return Response({"detail": str(exc), "code": exc.code}, status=400)
    return Response(
        {
            "course_id": course_id,
            "students": students,
            "teachers": teachers,
            "student_count": len(students),
            "teacher_count": len(teachers),
            "total_count": len(students) + len(teachers),
        }
    )


@api_view(["POST"])
@permission_classes([IsAdminOrStaff])
def add_student_to_course(request):
    """POST /api/classroom/add-student — enroll a student in a course."""
    course_id = (request.data.get("course_id") or "").strip()
    student_email = (request.data.get("student_email") or "").strip()
    if not course_id or not student_email:
        return Response({"detail": "course_id and student_email are required."}, status=400)

    service = ClassroomRosterService(request.user)
    try:
        result = service.add_student_to_course(course_id, student_email)
    except GoogleScopeMissingError as exc:
        return _scope_missing_response(exc)
    except ClassroomServiceError as exc:
        return Response({"detail": str(exc), "code": exc.code}, status=400)
    return Response(result)


@api_view(["POST"])
@permission_classes([IsAdminOrStaff])
def add_teacher_to_course(request):
    """POST /api/classroom/add-teacher — add a teacher to a course."""
    course_id = (request.data.get("course_id") or "").strip()
    teacher_email = (request.data.get("teacher_email") or "").strip()
    if not course_id or not teacher_email:
        return Response({"detail": "course_id and teacher_email are required."}, status=400)

    service = ClassroomRosterService(request.user)
    try:
        result = service.add_teacher_to_course(course_id, teacher_email)
    except GoogleScopeMissingError as exc:
        return _scope_missing_response(exc)
    except ClassroomServiceError as exc:
        return Response({"detail": str(exc), "code": exc.code}, status=400)
    return Response(result)


# ---------------------------------------------------------------------------
# Bundles API
# ---------------------------------------------------------------------------

@api_view(["GET"])
@permission_classes([IsAdminOrStaff])
def list_bundles(request):
    """GET /api/bundles — list all onboarding bundles."""
    active_only = request.query_params.get("active_only", "false").lower() == "true"
    qs = OnboardingBundle.objects.all().order_by("name")
    if active_only:
        qs = qs.filter(active=True)
    return Response(OnboardingBundleSerializer(qs, many=True).data)


@api_view(["POST"])
@permission_classes([IsAdminOrStaff])
def create_bundle(request):
    """POST /api/bundles — create an onboarding bundle."""
    ser = OnboardingBundleSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=400)
    ser.save(created_by=request.user)
    return Response(ser.data, status=201)


@api_view(["PATCH", "PUT"])
@permission_classes([IsAdminOrStaff])
def update_bundle(request, bundle_id):
    """PATCH /api/bundles/{id} — update an onboarding bundle."""
    try:
        bundle = OnboardingBundle.objects.get(id=bundle_id)
    except OnboardingBundle.DoesNotExist:
        return Response({"detail": "Bundle not found."}, status=404)
    ser = OnboardingBundleSerializer(bundle, data=request.data, partial=True)
    if not ser.is_valid():
        return Response(ser.errors, status=400)
    ser.save()
    return Response(ser.data)


@api_view(["DELETE"])
@permission_classes([IsAdminOrStaff])
def delete_bundle(request, bundle_id):
    """DELETE /api/bundles/{id} — delete a bundle."""
    try:
        bundle = OnboardingBundle.objects.get(id=bundle_id)
    except OnboardingBundle.DoesNotExist:
        return Response({"detail": "Bundle not found."}, status=404)
    bundle.delete()
    return Response(status=204)


# ---------------------------------------------------------------------------
# Commands API
# ---------------------------------------------------------------------------

@api_view(["POST"])
@permission_classes([IsAdminOrStaff])
def commands_preview(request):
    """POST /api/commands/preview — generate a preview for a given command type."""
    command_type = (request.data.get("command_type") or "").strip()
    params = request.data.get("params") or {}
    executor = CommandExecutor(request.user)

    try:
        if command_type == "ADD_USER_TO_GROUP":
            result = executor.preview_add_user_to_group(
                params.get("group_email", ""), params.get("user_email", "")
            )
        elif command_type == "REMOVE_USER_FROM_GROUP":
            result = executor.preview_remove_user_from_group(
                params.get("group_email", ""), params.get("user_email", "")
            )
        elif command_type == "ADD_STUDENT_TO_COURSE":
            result = executor.preview_add_student_to_course(
                params.get("course_id", ""), params.get("student_email", "")
            )
        elif command_type == "ADD_TEACHER_TO_COURSE":
            result = executor.preview_add_teacher_to_course(
                params.get("course_id", ""), params.get("teacher_email", "")
            )
        elif command_type == "ENROLL_GROUP_TO_COURSE":
            result = executor.preview_enroll_group_to_course(
                params.get("group_email", ""),
                params.get("course_id", ""),
                role=params.get("role", "student"),
            )
        elif command_type == "APPLY_ONBOARDING_BUNDLE":
            result = executor.preview_apply_bundle(
                params.get("user_email", ""), params.get("bundle_id")
            )
        elif command_type == "REMOVE_STUDENT_FROM_COURSE":
            result = executor.preview_remove_student(
                params.get("course_id", ""), params.get("student_email", "")
            )
        elif command_type == "REMOVE_TEACHER_FROM_COURSE":
            result = executor.preview_remove_teacher(
                params.get("course_id", ""), params.get("teacher_email", "")
            )
        else:
            return Response({"detail": f"Unknown command_type: {command_type}"}, status=400)
    except GoogleScopeMissingError as exc:
        return _scope_missing_response(exc)
    except (DirectoryServiceError, ClassroomServiceError, CommandExecutorError) as exc:
        return Response({"detail": str(exc)}, status=400)

    return Response(result)


@api_view(["POST"])
@permission_classes([IsAdminOrStaff])
def commands_run(request):
    """POST /api/commands/run — create and execute a command job."""
    command_type = (request.data.get("command_type") or "").strip()
    params = request.data.get("params") or {}
    dry_run = bool(request.data.get("dry_run", False))
    executor = CommandExecutor(request.user)

    try:
        if command_type == "ADD_USER_TO_GROUP":
            job = executor.build_add_user_to_group_job(
                params.get("group_email", ""), params.get("user_email", ""), dry_run=dry_run
            )
        elif command_type == "REMOVE_USER_FROM_GROUP":
            job = executor.build_remove_user_from_group_job(
                params.get("group_email", ""), params.get("user_email", ""), dry_run=dry_run
            )
        elif command_type == "ADD_STUDENT_TO_COURSE":
            job = executor.build_add_student_to_course_job(
                params.get("course_id", ""), params.get("student_email", ""), dry_run=dry_run
            )
        elif command_type == "ADD_TEACHER_TO_COURSE":
            job = executor.build_add_teacher_to_course_job(
                params.get("course_id", ""), params.get("teacher_email", ""), dry_run=dry_run
            )
        elif command_type == "ENROLL_GROUP_TO_COURSE":
            job = executor.build_enroll_group_to_course_job(
                params.get("group_email", ""),
                params.get("course_id", ""),
                role=params.get("role", "student"),
                dry_run=dry_run,
            )
        elif command_type == "APPLY_ONBOARDING_BUNDLE":
            job = executor.build_apply_bundle_job(
                params.get("user_email", ""), params.get("bundle_id"), dry_run=dry_run
            )
        elif command_type == "REMOVE_STUDENT_FROM_COURSE":
            job = executor.build_remove_student_from_course_job(
                params.get("course_id", ""), params.get("student_email", ""), dry_run=dry_run
            )
        elif command_type == "REMOVE_TEACHER_FROM_COURSE":
            job = executor.build_remove_teacher_from_course_job(
                params.get("course_id", ""), params.get("teacher_email", ""), dry_run=dry_run
            )
        else:
            return Response({"detail": f"Unknown command_type: {command_type}"}, status=400)
    except GoogleScopeMissingError as exc:
        return _scope_missing_response(exc)
    except (DirectoryServiceError, ClassroomServiceError, CommandExecutorError) as exc:
        return Response({"detail": str(exc)}, status=400)

    # Execute synchronously (Celery task queued via tasks.py when available)
    execute_command_job_task.delay(job.id)

    return Response(CommandJobSerializer(job).data, status=201)


@api_view(["GET"])
@permission_classes([IsAdminOrStaff])
def list_jobs(request):
    """GET /api/commands/jobs — list command jobs, newest first."""
    jobs = CommandJob.objects.filter(created_by=request.user).order_by("-created_at")
    return Response(CommandJobListSerializer(jobs, many=True).data)


@api_view(["GET"])
@permission_classes([IsAdminOrStaff])
def get_job(request, job_id):
    """GET /api/commands/jobs/{id} — get a single job with items."""
    try:
        job = CommandJob.objects.get(id=job_id, created_by=request.user)
    except CommandJob.DoesNotExist:
        return Response({"detail": "Job not found."}, status=404)
    return Response(CommandJobSerializer(job).data)


@api_view(["GET"])
@permission_classes([IsAdminOrStaff])
def list_command_logs(request):
    """GET /api/commands/logs — list all job items across jobs (audit log)."""
    items = (
        CommandJobItem.objects
        .filter(command_job__created_by=request.user)
        .select_related("command_job")
        .order_by("-created_at")[:200]
    )
    return Response(CommandJobItemSerializer(items, many=True).data)


@api_view(["POST"])
@permission_classes([IsAdminOrStaff])
def retry_job(request):
    """POST /api/commands/retry — retry failed items in a job."""
    job_id = request.data.get("job_id")
    if not job_id:
        return Response({"detail": "job_id is required."}, status=400)
    try:
        job = CommandJob.objects.get(id=job_id, created_by=request.user)
    except CommandJob.DoesNotExist:
        return Response({"detail": "Job not found."}, status=404)

    retry_command_job_task.delay(job.id)
    return Response({"message": "Retry queued.", "job_id": job.id})

@api_view(["POST"])
@permission_classes([IsAdminOrStaff])
def csv_import_preview(request):
    """POST /api/commands/import/csv/preview — parse CSV and return preview."""
    csv_text = request.data.get("csv_text") or ""
    if not csv_text.strip():
        return Response({"detail": "csv_text is required."}, status=400)

    default_bundle_id = request.data.get("default_bundle_id")
    executor = CommandExecutor(request.user)
    try:
        result = executor.preview_csv(csv_text, default_bundle_id=default_bundle_id)
    except CommandExecutorError as exc:
        return Response({"detail": str(exc), "code": exc.code}, status=400)
    return Response(result)


@api_view(["POST"])
@permission_classes([IsAdminOrStaff])
def csv_import_run(request):
    """POST /api/commands/import/csv/run — create and execute CSV onboarding job."""
    csv_text = request.data.get("csv_text") or ""
    if not csv_text.strip():
        return Response({"detail": "csv_text is required."}, status=400)

    default_bundle_id = request.data.get("default_bundle_id")
    dry_run = bool(request.data.get("dry_run", False))
    executor = CommandExecutor(request.user)

    try:
        job = executor.build_csv_onboarding_job(
            csv_text, default_bundle_id=default_bundle_id, dry_run=dry_run
        )
    except CommandExecutorError as exc:
        return Response({"detail": str(exc), "code": exc.code}, status=400)

    execute_command_job_task.delay(job.id)

    return Response(CommandJobSerializer(job).data, status=201)


# ---------------------------------------------------------------------------
# Phase 2B — Classroom Lifecycle + Direct Removal views
# ---------------------------------------------------------------------------

@api_view(["POST"])
@permission_classes([IsAdminOrStaff])
def classroom_preflight(request):
    """POST /api/classroom/preflight — validate a Classroom action before execution."""
    from .serializers import PreflightRequestSerializer
    ser = PreflightRequestSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=400)
    d = ser.validated_data
    action = d["action"]
    svc = ClassroomRosterService(request.user)
    kwargs = {}
    if d.get("course_id"):
        kwargs["course_id"] = d["course_id"]
    if d.get("name"):
        kwargs["name"] = d["name"]
    if d.get("student_email"):
        kwargs["student_email"] = d["student_email"]
    if d.get("teacher_email"):
        kwargs["teacher_email"] = d["teacher_email"]
    result = svc.preflight(action, **kwargs)
    return Response(result)


@api_view(["POST"])
@permission_classes([IsAdminOrStaff])
def create_course_view(request):
    """POST /api/classroom/courses/create — create a new Classroom course."""
    from .serializers import CreateCourseSerializer
    ser = CreateCourseSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=400)
    d = ser.validated_data
    svc = ClassroomRosterService(request.user)
    try:
        result = svc.create_course(**d)
    except GoogleScopeMissingError as exc:
        return _scope_missing_response(exc)
    except ClassroomServiceError as exc:
        return Response({"detail": str(exc), "code": exc.code}, status=400)
    # Audit via CommandJob
    executor = CommandExecutor(request.user)
    job = executor.create_job(
        ActionType.CREATE_COURSE,
        {"name": d["name"], "result": result.get("course", {}).get("id", "")},
    )
    item = executor._add_item(
        job, TargetType.COURSE,
        result.get("course", {}).get("id", d["name"]),
        ActionType.CREATE_COURSE,
        {"name": d["name"]},
    )
    from core.models import ItemStatus
    item.status = ItemStatus.SUCCESS
    item.result_json = result
    item.save(update_fields=["status", "result_json", "updated_at"])
    job.status = "completed"
    job.result_summary_json = {"success": 1, "skipped": 0, "failed": 0}
    job.save(update_fields=["status", "result_summary_json", "updated_at"])
    return Response(result, status=201)


@api_view(["POST"])
@permission_classes([IsAdminOrStaff])
def archive_course_view(request, course_id):
    """POST /api/classroom/courses/<id>/archive — archive a course."""
    svc = ClassroomRosterService(request.user)
    try:
        result = svc.archive_course(course_id)
    except GoogleScopeMissingError as exc:
        return _scope_missing_response(exc)
    except ClassroomServiceError as exc:
        return Response({"detail": str(exc), "code": exc.code}, status=400)
    executor = CommandExecutor(request.user)
    job = executor.create_job(ActionType.ARCHIVE_COURSE, {"course_id": course_id})
    item = executor._add_item(job, TargetType.COURSE, course_id, ActionType.ARCHIVE_COURSE, {"course_id": course_id})
    from core.models import ItemStatus
    item.status = ItemStatus.SKIPPED if result.get("skipped") else ItemStatus.SUCCESS
    item.result_json = result
    item.save(update_fields=["status", "result_json", "updated_at"])
    job.status = "completed"
    job.result_summary_json = {"success": 0 if result.get("skipped") else 1, "skipped": 1 if result.get("skipped") else 0, "failed": 0}
    job.save(update_fields=["status", "result_summary_json", "updated_at"])
    return Response(result)


@api_view(["DELETE"])
@permission_classes([IsAdminOrStaff])
def delete_course_view(request, course_id):
    """DELETE /api/classroom/courses/<id> — delete an archived course."""
    svc = ClassroomRosterService(request.user)
    try:
        result = svc.delete_course(course_id)
    except GoogleScopeMissingError as exc:
        return _scope_missing_response(exc)
    except ClassroomServiceError as exc:
        return Response({"detail": str(exc), "code": exc.code}, status=400)
    executor = CommandExecutor(request.user)
    job = executor.create_job(ActionType.DELETE_COURSE, {"course_id": course_id})
    item = executor._add_item(job, TargetType.COURSE, course_id, ActionType.DELETE_COURSE, {"course_id": course_id})
    from core.models import ItemStatus
    item.status = ItemStatus.SKIPPED if result.get("skipped") else ItemStatus.SUCCESS
    item.result_json = result
    item.save(update_fields=["status", "result_json", "updated_at"])
    job.status = "completed"
    job.result_summary_json = {"success": 0 if result.get("skipped") else 1, "skipped": 1 if result.get("skipped") else 0, "failed": 0}
    job.save(update_fields=["status", "result_summary_json", "updated_at"])
    return Response(result)


@api_view(["POST"])
@permission_classes([IsAdminOrStaff])
def remove_student_view(request):
    """POST /api/classroom/remove-student — directly remove a student from a course."""
    from .serializers import RemoveStudentSerializer
    ser = RemoveStudentSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=400)
    d = ser.validated_data
    svc = ClassroomRosterService(request.user)
    try:
        result = svc.remove_student_from_course(d["course_id"], d["student_email"])
    except GoogleScopeMissingError as exc:
        return _scope_missing_response(exc)
    except ClassroomServiceError as exc:
        return Response({"detail": str(exc), "code": exc.code}, status=400)
    executor = CommandExecutor(request.user)
    job = executor.build_remove_student_from_course_job(d["course_id"], d["student_email"])
    from core.models import ItemStatus
    item = job.items.first()
    if item:
        item.status = ItemStatus.SKIPPED if result.get("skipped") else ItemStatus.SUCCESS
        item.result_json = result
        item.save(update_fields=["status", "result_json", "updated_at"])
    job.status = "completed"
    job.result_summary_json = {"success": 0 if result.get("skipped") else 1, "skipped": 1 if result.get("skipped") else 0, "failed": 0}
    job.save(update_fields=["status", "result_summary_json", "updated_at"])
    return Response(result)


@api_view(["POST"])
@permission_classes([IsAdminOrStaff])
def remove_teacher_view(request):
    """POST /api/classroom/remove-teacher — directly remove a teacher from a course."""
    from .serializers import RemoveTeacherSerializer
    ser = RemoveTeacherSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=400)
    d = ser.validated_data
    svc = ClassroomRosterService(request.user)
    try:
        result = svc.remove_teacher_from_course(d["course_id"], d["teacher_email"])
    except GoogleScopeMissingError as exc:
        return _scope_missing_response(exc)
    except ClassroomServiceError as exc:
        return Response({"detail": str(exc), "code": exc.code}, status=400)
    executor = CommandExecutor(request.user)
    job = executor.build_remove_teacher_from_course_job(d["course_id"], d["teacher_email"])
    from core.models import ItemStatus
    item = job.items.first()
    if item:
        item.status = ItemStatus.SKIPPED if result.get("skipped") else ItemStatus.SUCCESS
        item.result_json = result
        item.save(update_fields=["status", "result_json", "updated_at"])
    job.status = "completed"
    job.result_summary_json = {"success": 0 if result.get("skipped") else 1, "skipped": 1 if result.get("skipped") else 0, "failed": 0}
    job.save(update_fields=["status", "result_summary_json", "updated_at"])
    return Response(result)

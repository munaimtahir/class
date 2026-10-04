from datetime import datetime

from celery import shared_task
from django.utils import timezone

from .google_client import GoogleService, GoogleServiceError
from .google_scopes import GoogleScopeMissingError
from .models import ClassroomPost, MeetEvent, PostLog, Session


def ensure_meet_event(session):
    if not session.meet_required:
        return None

    existing = getattr(session, "meet_event", None)
    if existing and existing.meet_link and existing.calendar_event_id:
        return existing

    start_dt = timezone.make_aware(datetime.combine(session.date, session.start_time))
    end_dt = timezone.make_aware(datetime.combine(session.date, session.end_time))

    google = GoogleService(session.course.user)
    event_id, meet_link = google.create_meet_event(session.title, start_dt, end_dt)

    meet_event, _ = MeetEvent.objects.update_or_create(
        session=session,
        defaults={
            "calendar_event_id": event_id,
            "meet_link": meet_link,
        },
    )
    PostLog.objects.create(session=session, status=Session.STATUS_PENDING, message="Meet link generated")
    return meet_event


@shared_task
def generate_meet_link(session_id):
    session = Session.objects.select_related("course__user").get(id=session_id)
    try:
        ensure_meet_event(session)
    except GoogleScopeMissingError as exc:
        session.status = Session.STATUS_FAILED
        session.save(update_fields=["status"])
        payload = exc.as_payload()
        PostLog.objects.create(
            session=session,
            status=Session.STATUS_FAILED,
            message=f"{payload['code']}: {payload['message']} (feature={payload['feature']})",
        )
        raise
    except GoogleServiceError as exc:
        session.status = Session.STATUS_FAILED
        session.save(update_fields=["status"])
        PostLog.objects.create(
            session=session,
            status=Session.STATUS_FAILED,
            message=f"{exc.code}: {str(exc)}",
        )
        raise
    except Exception as exc:
        session.status = Session.STATUS_FAILED
        session.save(update_fields=["status"])
        PostLog.objects.create(session=session, status=Session.STATUS_FAILED, message=str(exc))
        raise


@shared_task
def create_classroom_post(session_id, publish_now=False):
    session = Session.objects.select_related("course__user", "meet_event").get(id=session_id)
    try:
        meet_event = ensure_meet_event(session)
        meet_link = getattr(meet_event, "meet_link", "")
        google = GoogleService(session.course.user)

        scheduled_time = None
        if not publish_now:
            scheduled_time = timezone.make_aware(datetime.combine(session.date, session.start_time))

        post_id = google.create_classroom_material(
            course_id=session.course.google_course_id,
            title=session.title,
            description=f"{session.subject} - {session.topic}".strip(" -"),
            scheduled_time=scheduled_time,
            meet_link=meet_link,
        )

        status = Session.STATUS_POSTED if publish_now else Session.STATUS_SCHEDULED
        session.status = status
        session.save(update_fields=["status"])

        ClassroomPost.objects.update_or_create(
            session=session,
            defaults={
                "google_post_id": post_id,
                "scheduled_time": scheduled_time,
                "status": status,
            },
        )
        PostLog.objects.create(session=session, status=status, message="Classroom post created")
    except GoogleScopeMissingError as exc:
        session.status = Session.STATUS_FAILED
        session.save(update_fields=["status"])
        payload = exc.as_payload()
        PostLog.objects.create(
            session=session,
            status=Session.STATUS_FAILED,
            message=f"{payload['code']}: {payload['message']} (feature={payload['feature']})",
        )
        raise
    except GoogleServiceError as exc:
        session.status = Session.STATUS_FAILED
        session.save(update_fields=["status"])
        PostLog.objects.create(
            session=session,
            status=Session.STATUS_FAILED,
            message=f"{exc.code}: {str(exc)}",
        )
        raise
    except Exception as exc:
        session.status = Session.STATUS_FAILED
        session.save(update_fields=["status"])
        PostLog.objects.create(session=session, status=Session.STATUS_FAILED, message=str(exc))
        raise


@shared_task
def publish_scheduled_posts():
    now = timezone.now()
    posts = ClassroomPost.objects.select_related("session__course__user").filter(
        status=Session.STATUS_SCHEDULED,
        scheduled_time__lte=now,
    )
    for post in posts:
        create_classroom_post.delay(post.session_id, publish_now=True)


@shared_task
def retry_failed_posts():
    failed_sessions = Session.objects.filter(status=Session.STATUS_FAILED)
    for session in failed_sessions:
        create_classroom_post.delay(session.id, publish_now=True)


# ---------------------------------------------------------------------------
# Phase 2 — Command Job Celery Tasks
# ---------------------------------------------------------------------------


@shared_task
def execute_command_job_task(job_id: int):
    """Execute all pending items in a CommandJob."""
    from django.contrib.auth import get_user_model
    from .models import CommandJob
    from .services.command_executor import CommandExecutor

    try:
        job = CommandJob.objects.select_related("created_by").get(id=job_id)
    except CommandJob.DoesNotExist:
        return {"error": f"Job {job_id} not found"}

    executor = CommandExecutor(job.created_by)
    result = executor.execute_job(job)
    return result


@shared_task
def retry_command_job_task(job_id: int):
    """Retry all failed items in a CommandJob."""
    from .models import CommandJob
    from .services.command_executor import CommandExecutor

    try:
        job = CommandJob.objects.select_related("created_by").get(id=job_id)
    except CommandJob.DoesNotExist:
        return {"error": f"Job {job_id} not found"}

    executor = CommandExecutor(job.created_by)
    result = executor.retry_failed_items(job)
    return result


# ---------------------------------------------------------------------------
# Module B — Directory Operations Tasks
# ---------------------------------------------------------------------------


@shared_task
def directory_sync_task(user_id: int, query: str = "", max_results: int | None = None, sync_job_id: int | None = None):
    from django.contrib.auth import get_user_model
    from .models import DirectorySyncJob
    from .services.directory_module_service import DirectorySyncService

    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return {"error": f"user {user_id} not found"}
    sync_job = None
    if sync_job_id:
        try:
            sync_job = DirectorySyncJob.objects.get(id=sync_job_id)
        except DirectorySyncJob.DoesNotExist:
            sync_job = None
    return DirectorySyncService(user).sync_users(query=query, max_results=max_results, sync_job=sync_job)


@shared_task
def directory_issue_scan_task(user_ids: list[int] | None = None):
    from .models import DirectoryUser
    from .services.directory_module_service import InconsistencyDetectionService

    users = DirectoryUser.objects.filter(id__in=(user_ids or [])) if user_ids else None
    return InconsistencyDetectionService().scan(users=users)


@shared_task
def execute_directory_change_job_task(job_id: int):
    from .models import DirectoryChangeJob
    from .services.directory_module_service import DirectoryChangeService

    try:
        job = DirectoryChangeJob.objects.select_related("initiated_by").get(id=job_id)
    except DirectoryChangeJob.DoesNotExist:
        return {"error": f"directory change job {job_id} not found"}

    actor = job.initiated_by
    if actor is None:
        return {"error": "job has no initiating user"}

    service = DirectoryChangeService(actor)
    job = service.execute_existing_job(job)
    return job.execution_summary


@shared_task
def execute_provisioning_records_task(
    user_id: int,
    record_ids: list[int],
    dry_run: bool = False,
    approval_request_id: int | None = None,
):
    from django.contrib.auth import get_user_model
    from .models import ApprovalExecutionStatus, ApprovalRequest, ApprovalRequestStatus, ProvisioningRecord
    from .services.directory_module_service import ProvisioningService

    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return {"error": f"user {user_id} not found"}

    service = ProvisioningService(user)
    approval_request = None
    if approval_request_id:
        try:
            approval_request = ApprovalRequest.objects.get(id=approval_request_id)
        except ApprovalRequest.DoesNotExist:
            return {"error": f"approval request {approval_request_id} not found"}

    success = failed = 0
    for record in ProvisioningRecord.objects.filter(id__in=record_ids):
        updated = service.execute_record(record, dry_run=dry_run, approval_request=approval_request)
        if updated.status == "executed":
            success += 1
        elif updated.status == "failed":
            failed += 1
    if approval_request and not dry_run:
        if failed == 0 and success == len(record_ids):
            approval_request.status = ApprovalRequestStatus.EXECUTED
            approval_request.execution_status = ApprovalExecutionStatus.EXECUTED
            approval_request.execution_message = "Linked provisioning execution completed."
        else:
            approval_request.status = ApprovalRequestStatus.EXECUTION_FAILED
            approval_request.execution_status = ApprovalExecutionStatus.EXECUTION_FAILED
            approval_request.execution_message = f"Linked provisioning execution had failures: success={success}, failed={failed}."
        approval_request.save(update_fields=["status", "execution_status", "execution_message", "updated_at"])
    return {"total": len(record_ids), "success": success, "failed": failed, "dry_run": dry_run}

"""Phase 2 command executor.

Handles preview, job creation, item creation, execution, and result collection
for all supported Phase 2 admin command types.
"""

import csv
import io
import logging
from typing import Optional

from django.db import models

from core.models import (
    ActionType,
    CommandJob,
    CommandJobItem,
    ItemStatus,
    JobStatus,
    RoleType,
    TargetType,
)
from core.services.classroom_service import ClassroomRosterService, ClassroomServiceError
from core.services.google_directory_service import DirectoryServiceError, GoogleDirectoryService

logger = logging.getLogger(__name__)

CSV_REQUIRED_FIELDS = {"email"}
CSV_ALL_FIELDS = {"email", "name", "role", "bundle", "extra_groups", "extra_courses"}


class CommandExecutorError(Exception):
    def __init__(self, message: str, code: str = "executor_error"):
        super().__init__(message)
        self.code = code


class CommandExecutor:
    def __init__(self, user):
        self.user = user
        self._dir_service = GoogleDirectoryService(user)
        self._class_service = ClassroomRosterService(user)

    # ------------------------------------------------------------------
    # Preview helpers
    # ------------------------------------------------------------------

    def preview_add_user_to_group(self, group_email: str, user_email: str) -> dict:
        is_member = self._dir_service.is_member_of_group(group_email, user_email)
        return {
            "action": ActionType.ADD_USER_TO_GROUP,
            "group_email": group_email,
            "user_email": user_email,
            "would_skip": is_member,
            "skip_reason": "already_member" if is_member else None,
        }

    def preview_remove_user_from_group(self, group_email: str, user_email: str) -> dict:
        is_member = self._dir_service.is_member_of_group(group_email, user_email)
        return {
            "action": ActionType.REMOVE_USER_FROM_GROUP,
            "group_email": group_email,
            "user_email": user_email,
            "would_skip": not is_member,
            "skip_reason": "not_member" if not is_member else None,
        }

    def preview_add_student_to_course(self, course_id: str, student_email: str) -> dict:
        existing = self._class_service.list_students(course_id)
        skip = student_email.lower() in existing
        return {
            "action": ActionType.ADD_STUDENT_TO_COURSE,
            "course_id": course_id,
            "user_email": student_email,
            "would_skip": skip,
            "skip_reason": "already_enrolled" if skip else None,
        }

    def preview_add_teacher_to_course(self, course_id: str, teacher_email: str) -> dict:
        existing = self._class_service.list_teachers(course_id)
        skip = teacher_email.lower() in existing
        return {
            "action": ActionType.ADD_TEACHER_TO_COURSE,
            "course_id": course_id,
            "user_email": teacher_email,
            "would_skip": skip,
            "skip_reason": "already_teacher" if skip else None,
        }

    def preview_enroll_group_to_course(self, group_email: str, course_id: str, role: str = "student") -> dict:
        members = self._dir_service.list_group_members(group_email)
        member_emails = [m.get("email", "") for m in members if m.get("email")]

        if role == "teacher":
            existing = self._class_service.list_teachers(course_id)
        else:
            existing = self._class_service.list_students(course_id)

        to_enroll = [e for e in member_emails if e.lower() not in existing]
        to_skip = [e for e in member_emails if e.lower() in existing]

        return {
            "action": ActionType.ENROLL_GROUP_TO_COURSE,
            "group_email": group_email,
            "course_id": course_id,
            "role": role,
            "total_members": len(member_emails),
            "to_enroll": to_enroll,
            "to_skip": to_skip,
            "enroll_count": len(to_enroll),
            "skip_count": len(to_skip),
        }

    def preview_apply_bundle(self, user_email: str, bundle_id: int) -> dict:
        from core.models import OnboardingBundle
        try:
            bundle = OnboardingBundle.objects.get(id=bundle_id, active=True)
        except OnboardingBundle.DoesNotExist:
            raise CommandExecutorError(f"Bundle {bundle_id} not found or inactive.", "bundle_not_found")

        group_items = []
        for group_email in bundle.groups_json:
            is_member = self._dir_service.is_member_of_group(group_email, user_email)
            group_items.append({
                "group_email": group_email,
                "would_skip": is_member,
                "skip_reason": "already_member" if is_member else None,
            })

        course_items = []
        for course_id in bundle.classroom_courses_json:
            if bundle.role_type == RoleType.TEACHER:
                existing = self._class_service.list_teachers(course_id)
                skip = user_email.lower() in existing
                course_items.append({
                    "course_id": course_id,
                    "role": "teacher",
                    "would_skip": skip,
                    "skip_reason": "already_teacher" if skip else None,
                })
            else:
                existing = self._class_service.list_students(course_id)
                skip = user_email.lower() in existing
                course_items.append({
                    "course_id": course_id,
                    "role": "student",
                    "would_skip": skip,
                    "skip_reason": "already_enrolled" if skip else None,
                })

        return {
            "action": ActionType.APPLY_ONBOARDING_BUNDLE,
            "user_email": user_email,
            "bundle_id": bundle_id,
            "bundle_name": bundle.name,
            "group_items": group_items,
            "course_items": course_items,
            "total_actions": len(group_items) + len(course_items),
        }

    def preview_csv(self, csv_text: str, default_bundle_id: Optional[int] = None) -> dict:
        """Parse CSV and return row-by-row preview without executing."""
        reader = csv.DictReader(io.StringIO(csv_text.strip()))
        if not reader.fieldnames:
            raise CommandExecutorError("CSV has no headers.", "csv_no_headers")
        rows_ok = []
        rows_error = []
        for idx, row in enumerate(reader):
            email = (row.get("email") or "").strip()
            if not email:
                rows_error.append({"row": idx + 2, "error": "missing email", "data": dict(row)})
                continue
            role = (row.get("role") or "student").strip().lower()
            bundle_ref = (row.get("bundle") or "").strip()
            extra_groups = [g.strip() for g in (row.get("extra_groups") or "").split(",") if g.strip()]
            extra_courses = [c.strip() for c in (row.get("extra_courses") or "").split(",") if c.strip()]
            rows_ok.append({
                "row": idx + 2,
                "email": email,
                "name": (row.get("name") or "").strip(),
                "role": role,
                "bundle": bundle_ref or default_bundle_id,
                "extra_groups": extra_groups,
                "extra_courses": extra_courses,
            })
        return {
            "total_rows": len(rows_ok) + len(rows_error),
            "valid_rows": len(rows_ok),
            "error_rows": len(rows_error),
            "rows": rows_ok,
            "errors": rows_error,
        }

    # Phase 2B preview methods

    def preview_create_course(self, name: str, **kwargs) -> dict:
        result = self._class_service.preflight("create_course", name=name, **kwargs)
        result["action"] = ActionType.CREATE_COURSE
        result["name"] = name
        return result

    def preview_archive_course(self, course_id: str) -> dict:
        result = self._class_service.preflight("archive_course", course_id=course_id)
        result["action"] = ActionType.ARCHIVE_COURSE
        result["course_id"] = course_id
        return result

    def preview_delete_course(self, course_id: str) -> dict:
        result = self._class_service.preflight("delete_course", course_id=course_id)
        result["action"] = ActionType.DELETE_COURSE
        result["course_id"] = course_id
        return result

    def preview_remove_student(self, course_id: str, student_email: str) -> dict:
        result = self._class_service.preflight("remove_student", course_id=course_id, student_email=student_email)
        result["action"] = ActionType.REMOVE_STUDENT_FROM_COURSE
        result["course_id"] = course_id
        result["user_email"] = student_email
        return result

    def preview_remove_teacher(self, course_id: str, teacher_email: str) -> dict:
        result = self._class_service.preflight("remove_teacher", course_id=course_id, teacher_email=teacher_email)
        result["action"] = ActionType.REMOVE_TEACHER_FROM_COURSE
        result["course_id"] = course_id
        result["user_email"] = teacher_email
        return result

    # ------------------------------------------------------------------
    # Job creation
    # ------------------------------------------------------------------

    def create_job(self, job_type: str, target_summary: dict, dry_run: bool = False) -> CommandJob:
        job = CommandJob.objects.create(
            job_type=job_type,
            created_by=self.user,
            status=JobStatus.DRY_RUN if dry_run else JobStatus.PENDING,
            dry_run=dry_run,
            target_summary_json=target_summary,
        )
        return job

    def _add_item(self, job: CommandJob, target_type: str, target_ref: str, action: str, payload: dict):
        return CommandJobItem.objects.create(
            command_job=job,
            target_type=target_type,
            target_ref=target_ref,
            action=action,
            payload_json=payload,
            status=ItemStatus.PENDING,
        )

    # ------------------------------------------------------------------
    # Build job items for each command type
    # ------------------------------------------------------------------

    def build_add_user_to_group_job(self, group_email: str, user_email: str, dry_run: bool = False) -> CommandJob:
        job = self.create_job(
            ActionType.ADD_USER_TO_GROUP,
            {"group_email": group_email, "user_email": user_email},
            dry_run=dry_run,
        )
        self._add_item(job, TargetType.GROUP, group_email, ActionType.ADD_USER_TO_GROUP,
                       {"group_email": group_email, "user_email": user_email})
        return job

    def build_remove_user_from_group_job(self, group_email: str, user_email: str, dry_run: bool = False) -> CommandJob:
        job = self.create_job(
            ActionType.REMOVE_USER_FROM_GROUP,
            {"group_email": group_email, "user_email": user_email},
            dry_run=dry_run,
        )
        self._add_item(job, TargetType.GROUP, group_email, ActionType.REMOVE_USER_FROM_GROUP,
                       {"group_email": group_email, "user_email": user_email})
        return job

    def build_add_student_to_course_job(self, course_id: str, student_email: str, dry_run: bool = False) -> CommandJob:
        job = self.create_job(
            ActionType.ADD_STUDENT_TO_COURSE,
            {"course_id": course_id, "student_email": student_email},
            dry_run=dry_run,
        )
        self._add_item(job, TargetType.COURSE, course_id, ActionType.ADD_STUDENT_TO_COURSE,
                       {"course_id": course_id, "user_email": student_email})
        return job

    def build_add_teacher_to_course_job(self, course_id: str, teacher_email: str, dry_run: bool = False) -> CommandJob:
        job = self.create_job(
            ActionType.ADD_TEACHER_TO_COURSE,
            {"course_id": course_id, "teacher_email": teacher_email},
            dry_run=dry_run,
        )
        self._add_item(job, TargetType.COURSE, course_id, ActionType.ADD_TEACHER_TO_COURSE,
                       {"course_id": course_id, "user_email": teacher_email})
        return job

    def build_enroll_group_to_course_job(
        self, group_email: str, course_id: str, role: str = "student", dry_run: bool = False
    ) -> CommandJob:
        members = self._dir_service.list_group_members(group_email)
        member_emails = [m.get("email", "") for m in members if m.get("email")]
        job = self.create_job(
            ActionType.ENROLL_GROUP_TO_COURSE,
            {"group_email": group_email, "course_id": course_id, "role": role, "member_count": len(member_emails)},
            dry_run=dry_run,
        )
        action = ActionType.ADD_TEACHER_TO_COURSE if role == "teacher" else ActionType.ADD_STUDENT_TO_COURSE
        for email in member_emails:
            self._add_item(job, TargetType.USER, email, action,
                           {"course_id": course_id, "user_email": email, "role": role})
        return job

    def build_apply_bundle_job(self, user_email: str, bundle_id: int, dry_run: bool = False) -> CommandJob:
        from core.models import OnboardingBundle
        try:
            bundle = OnboardingBundle.objects.get(id=bundle_id, active=True)
        except OnboardingBundle.DoesNotExist:
            raise CommandExecutorError(f"Bundle {bundle_id} not found or inactive.", "bundle_not_found")

        job = self.create_job(
            ActionType.APPLY_ONBOARDING_BUNDLE,
            {"user_email": user_email, "bundle_id": bundle_id, "bundle_name": bundle.name},
            dry_run=dry_run,
        )
        for group_email in bundle.groups_json:
            self._add_item(job, TargetType.GROUP, group_email, ActionType.ADD_USER_TO_GROUP,
                           {"group_email": group_email, "user_email": user_email})
        action = ActionType.ADD_TEACHER_TO_COURSE if bundle.role_type == RoleType.TEACHER else ActionType.ADD_STUDENT_TO_COURSE
        for course_id in bundle.classroom_courses_json:
            self._add_item(job, TargetType.COURSE, course_id, action,
                           {"course_id": course_id, "user_email": user_email})
        return job

    def build_csv_onboarding_job(
        self, csv_text: str, default_bundle_id: Optional[int] = None, dry_run: bool = False
    ) -> CommandJob:
        from core.models import OnboardingBundle
        preview = self.preview_csv(csv_text, default_bundle_id)
        job = self.create_job(
            ActionType.BULK_CSV_ONBOARDING,
            {
                "total_rows": preview["total_rows"],
                "valid_rows": preview["valid_rows"],
                "error_rows": preview["error_rows"],
                "csv_errors": preview["errors"],
            },
            dry_run=dry_run,
        )
        for row in preview["rows"]:
            user_email = row["email"]
            role = row.get("role", "student")

            bundle_ref = row.get("bundle")
            if bundle_ref:
                try:
                    bundle_id_val = int(bundle_ref)
                    bundle = OnboardingBundle.objects.filter(id=bundle_id_val, active=True).first()
                except (ValueError, TypeError):
                    bundle = OnboardingBundle.objects.filter(name__iexact=str(bundle_ref), active=True).first()

                if bundle:
                    for group_email in bundle.groups_json:
                        self._add_item(job, TargetType.GROUP, group_email, ActionType.ADD_USER_TO_GROUP,
                                       {"group_email": group_email, "user_email": user_email})
                    action = ActionType.ADD_TEACHER_TO_COURSE if bundle.role_type == RoleType.TEACHER else ActionType.ADD_STUDENT_TO_COURSE
                    for course_id in bundle.classroom_courses_json:
                        self._add_item(job, TargetType.COURSE, course_id, action,
                                       {"course_id": course_id, "user_email": user_email})

            # Extra groups / courses from CSV columns
            action_for_role = ActionType.ADD_TEACHER_TO_COURSE if role == "teacher" else ActionType.ADD_STUDENT_TO_COURSE
            for group_email in row.get("extra_groups", []):
                self._add_item(job, TargetType.GROUP, group_email, ActionType.ADD_USER_TO_GROUP,
                               {"group_email": group_email, "user_email": user_email})
            for course_id in row.get("extra_courses", []):
                self._add_item(job, TargetType.COURSE, course_id, action_for_role,
                               {"course_id": course_id, "user_email": user_email})

        return job

    # Phase 2B job builders

    def build_remove_student_from_course_job(
        self, course_id: str, student_email: str, dry_run: bool = False
    ) -> CommandJob:
        job = self.create_job(
            ActionType.REMOVE_STUDENT_FROM_COURSE,
            {"course_id": course_id, "student_email": student_email},
            dry_run=dry_run,
        )
        self._add_item(job, TargetType.USER, student_email, ActionType.REMOVE_STUDENT_FROM_COURSE,
                       {"course_id": course_id, "user_email": student_email})
        return job

    def build_remove_teacher_from_course_job(
        self, course_id: str, teacher_email: str, dry_run: bool = False
    ) -> CommandJob:
        job = self.create_job(
            ActionType.REMOVE_TEACHER_FROM_COURSE,
            {"course_id": course_id, "teacher_email": teacher_email},
            dry_run=dry_run,
        )
        self._add_item(job, TargetType.USER, teacher_email, ActionType.REMOVE_TEACHER_FROM_COURSE,
                       {"course_id": course_id, "user_email": teacher_email})
        return job

    def build_archive_course_job(self, course_id: str, dry_run: bool = False) -> CommandJob:
        job = self.create_job(
            ActionType.ARCHIVE_COURSE,
            {"course_id": course_id},
            dry_run=dry_run,
        )
        self._add_item(job, TargetType.COURSE, course_id, ActionType.ARCHIVE_COURSE,
                       {"course_id": course_id})
        return job

    def build_delete_course_job(self, course_id: str, dry_run: bool = False) -> CommandJob:
        job = self.create_job(
            ActionType.DELETE_COURSE,
            {"course_id": course_id},
            dry_run=dry_run,
        )
        self._add_item(job, TargetType.COURSE, course_id, ActionType.DELETE_COURSE,
                       {"course_id": course_id})
        return job

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute_job(self, job: CommandJob) -> dict:
        """Execute all pending items in a CommandJob."""
        if job.dry_run:
            job.status = JobStatus.DRY_RUN
            job.result_summary_json = {"message": "dry_run — no changes made"}
            job.save(update_fields=["status", "result_summary_json"])
            return job.result_summary_json

        job.status = JobStatus.RUNNING
        job.save(update_fields=["status"])

        items = job.items.filter(status=ItemStatus.PENDING)
        success = skipped = failed = 0

        for item in items:
            try:
                result = self._execute_item(item)
                if result.get("skipped"):
                    item.status = ItemStatus.SKIPPED
                else:
                    item.status = ItemStatus.SUCCESS
                    success += 1
                    if result.get("skipped"):
                        skipped += 1
                item.result_json = result
            except (DirectoryServiceError, ClassroomServiceError, Exception) as exc:
                item.status = ItemStatus.FAILED
                item.result_json = {"error": str(exc)}
                failed += 1
                logger.error("Item %s failed: %s", item.pk, exc)
            item.save(update_fields=["status", "result_json", "updated_at"])

        # Recount skipped
        skipped = job.items.filter(status=ItemStatus.SKIPPED).count()
        success = job.items.filter(status=ItemStatus.SUCCESS).count()
        failed = job.items.filter(status=ItemStatus.FAILED).count()

        summary = {
            "total": job.items.count(),
            "success": success,
            "skipped": skipped,
            "failed": failed,
        }
        if failed > 0 and success == 0:
            job.status = JobStatus.FAILED
        elif failed > 0:
            job.status = JobStatus.PARTIAL
        else:
            job.status = JobStatus.COMPLETED

        job.result_summary_json = summary
        job.save(update_fields=["status", "result_summary_json", "updated_at"])
        return summary

    def _execute_item(self, item: CommandJobItem) -> dict:
        """Dispatch execution for a single item based on its action type."""
        payload = item.payload_json
        action = item.action

        if action == ActionType.ADD_USER_TO_GROUP:
            return self._dir_service.add_member_to_group(
                payload["group_email"], payload["user_email"]
            )
        elif action == ActionType.REMOVE_USER_FROM_GROUP:
            return self._dir_service.remove_member_from_group(
                payload["group_email"], payload["user_email"]
            )
        elif action == ActionType.ADD_STUDENT_TO_COURSE:
            return self._class_service.add_student_to_course(
                payload["course_id"], payload["user_email"]
            )
        elif action == ActionType.ADD_TEACHER_TO_COURSE:
            return self._class_service.add_teacher_to_course(
                payload["course_id"], payload["user_email"]
            )
        # Phase 2B
        elif action == ActionType.REMOVE_STUDENT_FROM_COURSE:
            return self._class_service.remove_student_from_course(
                payload["course_id"], payload["user_email"]
            )
        elif action == ActionType.REMOVE_TEACHER_FROM_COURSE:
            return self._class_service.remove_teacher_from_course(
                payload["course_id"], payload["user_email"]
            )
        elif action == ActionType.ARCHIVE_COURSE:
            return self._class_service.archive_course(payload["course_id"])
        elif action == ActionType.DELETE_COURSE:
            return self._class_service.delete_course(payload["course_id"])
        elif action == ActionType.CREATE_COURSE:
            return self._class_service.create_course(
                name=payload.get("name", ""),
                section=payload.get("section", ""),
                description_heading=payload.get("description_heading", ""),
                description=payload.get("description", ""),
                room=payload.get("room", ""),
                owner_id=payload.get("owner_id", "me"),
            )
        else:
            raise CommandExecutorError(f"Unknown action: {action}")

    def retry_failed_items(self, job: CommandJob) -> dict:
        """Re-queue and execute only failed items in a job."""
        failed_items = job.items.filter(status=ItemStatus.FAILED)
        if not failed_items.exists():
            return {"message": "No failed items to retry.", "retried": 0}

        failed_items.update(status=ItemStatus.PENDING, retry_count=models.F("retry_count") + 1)

        # Re-execute
        return self.execute_job(job)

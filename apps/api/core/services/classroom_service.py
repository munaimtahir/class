"""Phase 2 Classroom roster service.

Uses the authenticated user's OAuth credentials with Classroom roster scopes.

Required OAuth scopes:
  https://www.googleapis.com/auth/classroom.rosters
  https://www.googleapis.com/auth/classroom.profile.emails
  https://www.googleapis.com/auth/classroom.courses.readonly
"""

import logging

from googleapiclient.errors import HttpError

from core.google_client import GoogleService

logger = logging.getLogger(__name__)


class ClassroomServiceError(Exception):
    def __init__(self, message: str, code: str = "classroom_error"):
        super().__init__(message)
        self.code = code


class ClassroomRosterService:
    def __init__(self, user):
        self.user = user
        self._google = GoogleService(user)

    def _classroom(self):
        return self._google.classroom()

    # ------------------------------------------------------------------
    # Courses
    # ------------------------------------------------------------------

    def list_courses(self) -> list[dict]:
        """List all active courses the authenticated user has access to (as teacher or admin)."""
        self._google.require_feature_scope("list_courses")
        try:
            service = self._classroom()
            results = []
            page_token = None
            while True:
                kwargs = {"courseStates": ["ACTIVE"], "pageSize": 100}
                if page_token:
                    kwargs["pageToken"] = page_token
                resp = service.courses().list(**kwargs).execute()
                results.extend(resp.get("courses", []))
                page_token = resp.get("nextPageToken")
                if not page_token:
                    break
            return results
        except HttpError as exc:
            logger.error("list_courses failed: %s", exc)
            raise ClassroomServiceError(str(exc))

    # ------------------------------------------------------------------
    # Students
    # ------------------------------------------------------------------

    def list_students(self, course_id: str) -> list[str]:
        """Return a list of student email addresses enrolled in a course."""
        self._google.require_feature_scope("list_roster")
        try:
            service = self._classroom()
            results = []
            page_token = None
            while True:
                kwargs = {"courseId": course_id, "pageSize": 200}
                if page_token:
                    kwargs["pageToken"] = page_token
                resp = service.courses().students().list(**kwargs).execute()
                for s in resp.get("students", []):
                    email = (s.get("profile") or {}).get("emailAddress", "")
                    if email:
                        results.append(email.lower())
                page_token = resp.get("nextPageToken")
                if not page_token:
                    break
            return results
        except HttpError as exc:
            logger.error("list_students(%s) failed: %s", course_id, exc)
            raise ClassroomServiceError(str(exc))

    def add_student_to_course(self, course_id: str, student_email: str) -> dict:
        """Enroll a student in a Classroom course. Skips if already enrolled."""
        self._google.require_feature_scope("bulk_add_students")
        existing = self.list_students(course_id)
        if student_email.lower() in existing:
            return {"skipped": True, "reason": "already_enrolled", "email": student_email}
        try:
            service = self._classroom()
            body = {"userId": student_email}
            result = service.courses().students().create(
                courseId=course_id, body=body
            ).execute()
            return {"success": True, "student": result}
        except HttpError as exc:
            # 409 = already a member
            if exc.resp.status == 409:
                return {"skipped": True, "reason": "already_enrolled", "email": student_email}
            logger.error("add_student_to_course(%s, %s) failed: %s", course_id, student_email, exc)
            raise ClassroomServiceError(str(exc))

    # ------------------------------------------------------------------
    # Teachers
    # ------------------------------------------------------------------

    def list_teachers(self, course_id: str) -> list[str]:
        """Return a list of teacher email addresses in a course."""
        self._google.require_feature_scope("list_roster")
        try:
            service = self._classroom()
            results = []
            page_token = None
            while True:
                kwargs = {"courseId": course_id, "pageSize": 200}
                if page_token:
                    kwargs["pageToken"] = page_token
                resp = service.courses().teachers().list(**kwargs).execute()
                for t in resp.get("teachers", []):
                    email = (t.get("profile") or {}).get("emailAddress", "")
                    if email:
                        results.append(email.lower())
                page_token = resp.get("nextPageToken")
                if not page_token:
                    break
            return results
        except HttpError as exc:
            logger.error("list_teachers(%s) failed: %s", course_id, exc)
            raise ClassroomServiceError(str(exc))

    def add_teacher_to_course(self, course_id: str, teacher_email: str) -> dict:
        """Add a teacher to a Classroom course. Skips if already a teacher."""
        self._google.require_feature_scope("add_teacher")
        existing = self.list_teachers(course_id)
        if teacher_email.lower() in existing:
            return {"skipped": True, "reason": "already_teacher", "email": teacher_email}
        try:
            service = self._classroom()
            body = {"userId": teacher_email}
            result = service.courses().teachers().create(
                courseId=course_id, body=body
            ).execute()
            return {"success": True, "teacher": result}
        except HttpError as exc:
            if exc.resp.status == 409:
                return {"skipped": True, "reason": "already_teacher", "email": teacher_email}
            logger.error("add_teacher_to_course(%s, %s) failed: %s", course_id, teacher_email, exc)
            raise ClassroomServiceError(str(exc))

    # ------------------------------------------------------------------
    # Phase 2B — Course Lifecycle
    # ------------------------------------------------------------------

    def get_course(self, course_id: str) -> dict:
        """Fetch a single course by ID. Raises ClassroomServiceError if not found."""
        self._google.require_feature_scope("list_courses")
        try:
            service = self._classroom()
            return service.courses().get(id=course_id).execute()
        except HttpError as exc:
            if exc.resp.status == 404:
                raise ClassroomServiceError(
                    f"Course {course_id!r} not found.", code="course_not_found"
                )
            logger.error("get_course(%s) failed: %s", course_id, exc)
            raise ClassroomServiceError(str(exc))

    def create_course(
        self,
        name: str,
        section: str = "",
        description_heading: str = "",
        description: str = "",
        room: str = "",
        owner_id: str = "me",
    ) -> dict:
        """Create a new Classroom course. Returns the created course object."""
        self._google.require_feature_scope("create_course")
        if not name or not name.strip():
            raise ClassroomServiceError("Course name is required.", code="missing_name")
        body = {
            "name": name.strip(),
            "ownerId": owner_id or "me",
        }
        if section:
            body["section"] = section.strip()
        if description_heading:
            body["descriptionHeading"] = description_heading.strip()
        if description:
            body["description"] = description.strip()
        if room:
            body["room"] = room.strip()
        try:
            service = self._classroom()
            course = service.courses().create(body=body).execute()
            return {"success": True, "course": course}
        except HttpError as exc:
            logger.error("create_course(%s) failed: %s", name, exc)
            raise ClassroomServiceError(str(exc))

    def archive_course(self, course_id: str) -> dict:
        """Archive a course. Skips if already archived."""
        self._google.require_feature_scope("archive_course")
        course = self.get_course(course_id)
        state = course.get("courseState", "")
        if state == "ARCHIVED":
            return {"skipped": True, "reason": "already_archived", "course_id": course_id}
        if state == "DELETED":
            raise ClassroomServiceError(
                f"Course {course_id!r} is deleted and cannot be archived.", code="course_deleted"
            )
        try:
            service = self._classroom()
            updated = service.courses().patch(
                id=course_id,
                updateMask="courseState",
                body={"courseState": "ARCHIVED"},
            ).execute()
            return {"success": True, "course": updated}
        except HttpError as exc:
            logger.error("archive_course(%s) failed: %s", course_id, exc)
            raise ClassroomServiceError(str(exc))

    def delete_course(self, course_id: str) -> dict:
        """Delete a course. The course must be ARCHIVED first (Classroom API requirement)."""
        self._google.require_feature_scope("delete_course")
        course = self.get_course(course_id)
        state = course.get("courseState", "")
        if state not in ("ARCHIVED", "ACTIVE"):
            raise ClassroomServiceError(
                f"Course {course_id!r} has state {state!r} and cannot be deleted.",
                code="invalid_course_state",
            )
        if state == "ACTIVE":
            raise ClassroomServiceError(
                "Active courses must be archived before deletion. Archive the course first.",
                code="must_archive_first",
            )
        try:
            service = self._classroom()
            service.courses().delete(id=course_id).execute()
            return {"success": True, "course_id": course_id, "deleted": True}
        except HttpError as exc:
            if exc.resp.status == 404:
                return {"skipped": True, "reason": "already_deleted", "course_id": course_id}
            logger.error("delete_course(%s) failed: %s", course_id, exc)
            raise ClassroomServiceError(str(exc))

    # ------------------------------------------------------------------
    # Phase 2B — Direct Removal
    # ------------------------------------------------------------------

    def remove_student_from_course(self, course_id: str, student_email: str) -> dict:
        """Remove a student from a Classroom course. Skips if not enrolled."""
        self._google.require_feature_scope("bulk_add_students")
        existing = self.list_students(course_id)
        if student_email.lower() not in existing:
            return {"skipped": True, "reason": "not_enrolled", "email": student_email}
        try:
            service = self._classroom()
            service.courses().students().delete(
                courseId=course_id, userId=student_email
            ).execute()
            return {"success": True, "email": student_email, "course_id": course_id}
        except HttpError as exc:
            if exc.resp.status == 404:
                return {"skipped": True, "reason": "not_enrolled", "email": student_email}
            logger.error("remove_student_from_course(%s, %s) failed: %s", course_id, student_email, exc)
            raise ClassroomServiceError(str(exc))

    def remove_teacher_from_course(self, course_id: str, teacher_email: str) -> dict:
        """Remove a teacher from a Classroom course. Skips if not a teacher."""
        self._google.require_feature_scope("add_teacher")
        existing = self.list_teachers(course_id)
        if teacher_email.lower() not in existing:
            return {"skipped": True, "reason": "not_teacher", "email": teacher_email}
        try:
            service = self._classroom()
            service.courses().teachers().delete(
                courseId=course_id, userId=teacher_email
            ).execute()
            return {"success": True, "email": teacher_email, "course_id": course_id}
        except HttpError as exc:
            if exc.resp.status == 404:
                return {"skipped": True, "reason": "not_teacher", "email": teacher_email}
            if exc.resp.status == 400:
                # Google rejects removing the course owner
                raise ClassroomServiceError(
                    "Cannot remove the course owner as a teacher.", code="cannot_remove_owner"
                )
            logger.error("remove_teacher_from_course(%s, %s) failed: %s", course_id, teacher_email, exc)
            raise ClassroomServiceError(str(exc))

    # ------------------------------------------------------------------
    # Phase 2B — Preflight Validation
    # ------------------------------------------------------------------

    def preflight(self, action: str, **kwargs) -> dict:
        """
        Run preflight validation for a Classroom action.

        Returns:
            {
                "allowed": bool,
                "warnings": [...],
                "errors": [...],
                "metadata": {...}
            }
        """
        allowed = True
        warnings = []
        errors = []
        metadata = {}

        try:
            if action == "create_course":
                name = (kwargs.get("name") or "").strip()
                if not name:
                    errors.append("Course name is required.")
                    allowed = False
                else:
                    metadata["name"] = name

            elif action == "archive_course":
                course_id = kwargs.get("course_id", "")
                course = self.get_course(course_id)
                state = course.get("courseState", "")
                metadata["course_name"] = course.get("name", "")
                metadata["current_state"] = state
                if state == "ARCHIVED":
                    warnings.append("Course is already archived.")
                    allowed = False
                elif state == "DELETED":
                    errors.append("Course is deleted and cannot be archived.")
                    allowed = False

            elif action == "delete_course":
                course_id = kwargs.get("course_id", "")
                course = self.get_course(course_id)
                state = course.get("courseState", "")
                metadata["course_name"] = course.get("name", "")
                metadata["current_state"] = state
                if state == "ACTIVE":
                    errors.append("Active courses must be archived before deletion.")
                    allowed = False
                elif state not in ("ARCHIVED",):
                    errors.append(f"Course state {state!r} does not permit deletion.")
                    allowed = False

            elif action == "remove_student":
                course_id = kwargs.get("course_id", "")
                student_email = (kwargs.get("student_email") or "").strip()
                course = self.get_course(course_id)
                metadata["course_name"] = course.get("name", "")
                enrolled = self.list_students(course_id)
                metadata["is_enrolled"] = student_email.lower() in enrolled
                if not metadata["is_enrolled"]:
                    warnings.append(f"{student_email!r} is not enrolled in this course.")

            elif action == "remove_teacher":
                course_id = kwargs.get("course_id", "")
                teacher_email = (kwargs.get("teacher_email") or "").strip()
                course = self.get_course(course_id)
                metadata["course_name"] = course.get("name", "")
                metadata["course_owner"] = (course.get("ownerId") or "").lower()
                teachers = self.list_teachers(course_id)
                metadata["is_teacher"] = teacher_email.lower() in teachers
                if not metadata["is_teacher"]:
                    warnings.append(f"{teacher_email!r} is not a teacher in this course.")
                if teacher_email.lower() == metadata["course_owner"]:
                    errors.append("Cannot remove the course owner as a teacher.")
                    allowed = False

            else:
                errors.append(f"Unknown preflight action: {action!r}")
                allowed = False

        except ClassroomServiceError as exc:
            errors.append(str(exc))
            allowed = False

        return {"allowed": allowed, "warnings": warnings, "errors": errors, "metadata": metadata}

from datetime import datetime

from django.conf import settings
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .google_scopes import (
    GoogleScopeMissingError,
    required_scopes_for_feature,
    validate_scopes,
)


class GoogleServiceError(Exception):
    def __init__(self, message: str, code: str = "google_error"):
        super().__init__(message)
        self.code = code


def normalize_user_scopes(user) -> list[str]:
    if getattr(user, "google_scopes_json", None):
        return [scope for scope in user.google_scopes_json if isinstance(scope, str)]
    if user.google_scopes:
        return [scope for scope in user.google_scopes.split() if scope]
    return []


class GoogleService:
    def __init__(self, user):
        self.user = user

    def granted_scopes(self) -> list[str]:
        return normalize_user_scopes(self.user)

    def require_feature_scope(self, feature: str):
        required = required_scopes_for_feature(feature)
        result = validate_scopes(self.granted_scopes(), required)
        if not result.ok:
            raise GoogleScopeMissingError(feature=feature, missing_scopes=result.missing)

    def credentials(self):
        return Credentials(
            token=self.user.access_token,
            refresh_token=self.user.get_refresh_token(),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            scopes=self.granted_scopes(),
        )

    def admin_directory(self):
        return build("admin", "directory_v1", credentials=self.credentials(), cache_discovery=False)

    def classroom(self):
        return build("classroom", "v1", credentials=self.credentials(), cache_discovery=False)

    def calendar(self):
        return build("calendar", "v3", credentials=self.credentials(), cache_discovery=False)

    def list_courses(self):
        self.require_feature_scope("list_courses")
        service = self.classroom()
        response = service.courses().list(courseStates=["ACTIVE"], teacherId="me").execute()
        return response.get("courses", [])

    def create_meet_event(self, title, start_dt, end_dt):
        self.require_feature_scope("create_calendar_event")
        service = self.calendar()
        event = {
            "summary": title,
            "start": {"dateTime": start_dt.isoformat(), "timeZone": settings.TIME_ZONE},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": settings.TIME_ZONE},
            "conferenceData": {
                "createRequest": {
                    "requestId": f"class-{int(datetime.utcnow().timestamp())}-{title[:8]}",
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            },
        }
        try:
            created = (
                service.events()
                .insert(
                    calendarId="primary",
                    body=event,
                    conferenceDataVersion=1,
                )
                .execute()
            )
        except HttpError as exc:
            raise GoogleServiceError(f"Calendar event creation failed: {exc}", "calendar_error") from exc
        meet_link = ((created.get("conferenceData") or {}).get("entryPoints") or [{}])[0].get("uri", "")
        return created.get("id"), meet_link

    def create_classroom_material(self, course_id, title, description, scheduled_time=None, meet_link=""):
        self.require_feature_scope("create_course_material")
        service = self.classroom()
        body = {
            "title": title,
            "description": f"{description}\n\nMeet: {meet_link}" if meet_link else description,
            "state": "PUBLISHED" if not scheduled_time else "DRAFT",
        }
        if scheduled_time:
            body["scheduledTime"] = scheduled_time.isoformat()
        try:
            material = service.courses().courseWorkMaterials().create(courseId=course_id, body=body).execute()
        except HttpError as exc:
            raise GoogleServiceError(f"Classroom material creation failed: {exc}", "classroom_material_error") from exc
        return material.get("id")

    def create_classroom_announcement(self, course_id: str, text: str) -> str:
        self.require_feature_scope("create_class_announcement")
        service = self.classroom()
        body = {"text": text, "state": "PUBLISHED"}
        try:
            announcement = (
                service.courses().announcements().create(courseId=course_id, body=body).execute()
            )
        except HttpError as exc:
            raise GoogleServiceError(f"Classroom announcement creation failed: {exc}", "classroom_announcement_error") from exc
        return announcement.get("id", "")

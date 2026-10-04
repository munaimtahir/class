from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


SCOPE_OPENID = "openid"
SCOPE_EMAIL = "email"
SCOPE_PROFILE = "profile"

SCOPE_CLASSROOM_COURSES = "https://www.googleapis.com/auth/classroom.courses"
SCOPE_CLASSROOM_COURSES_READONLY = "https://www.googleapis.com/auth/classroom.courses.readonly"
SCOPE_CLASSROOM_ROSTERS = "https://www.googleapis.com/auth/classroom.rosters"
SCOPE_CLASSROOM_ROSTERS_READONLY = "https://www.googleapis.com/auth/classroom.rosters.readonly"
SCOPE_CLASSROOM_COURSEWORK_MATERIALS = "https://www.googleapis.com/auth/classroom.courseworkmaterials"
SCOPE_CLASSROOM_COURSEWORK_MATERIALS_READONLY = "https://www.googleapis.com/auth/classroom.courseworkmaterials.readonly"
SCOPE_CLASSROOM_PROFILE_EMAILS = "https://www.googleapis.com/auth/classroom.profile.emails"
SCOPE_CLASSROOM_PROFILE_PHOTOS = "https://www.googleapis.com/auth/classroom.profile.photos"
SCOPE_CLASSROOM_ANNOUNCEMENTS = "https://www.googleapis.com/auth/classroom.announcements"
SCOPE_CLASSROOM_ANNOUNCEMENTS_READONLY = "https://www.googleapis.com/auth/classroom.announcements.readonly"
SCOPE_CALENDAR = "https://www.googleapis.com/auth/calendar"
SCOPE_SPREADSHEETS_READONLY = "https://www.googleapis.com/auth/spreadsheets.readonly"

SCOPE_ADMIN_GROUP_READONLY = "https://www.googleapis.com/auth/admin.directory.group.readonly"
SCOPE_ADMIN_GROUP_MEMBER = "https://www.googleapis.com/auth/admin.directory.group.member"
SCOPE_ADMIN_GROUP_MEMBER_READONLY = "https://www.googleapis.com/auth/admin.directory.group.member.readonly"
SCOPE_ADMIN_USER_READONLY = "https://www.googleapis.com/auth/admin.directory.user.readonly"
SCOPE_ADMIN_USER = "https://www.googleapis.com/auth/admin.directory.user"
SCOPE_ADMIN_ORGUNIT_READONLY = "https://www.googleapis.com/auth/admin.directory.orgunit.readonly"
SCOPE_ADMIN_ORGUNIT = "https://www.googleapis.com/auth/admin.directory.orgunit"


AUTH_IDENTITY_SCOPES = [SCOPE_OPENID, SCOPE_EMAIL, SCOPE_PROFILE]

APP_OPERATIONAL_SCOPES = [
    SCOPE_CLASSROOM_COURSES,
    SCOPE_CLASSROOM_COURSES_READONLY,
    SCOPE_CLASSROOM_ROSTERS,
    SCOPE_CLASSROOM_ROSTERS_READONLY,
    SCOPE_CLASSROOM_COURSEWORK_MATERIALS,
    SCOPE_CLASSROOM_COURSEWORK_MATERIALS_READONLY,
    SCOPE_CLASSROOM_PROFILE_EMAILS,
    SCOPE_CLASSROOM_PROFILE_PHOTOS,
    SCOPE_CLASSROOM_ANNOUNCEMENTS,
    SCOPE_CLASSROOM_ANNOUNCEMENTS_READONLY,
    SCOPE_CALENDAR,
    SCOPE_SPREADSHEETS_READONLY,
    SCOPE_ADMIN_GROUP_READONLY,
    SCOPE_ADMIN_GROUP_MEMBER,
    SCOPE_ADMIN_GROUP_MEMBER_READONLY,
    SCOPE_ADMIN_USER_READONLY,
    SCOPE_ADMIN_USER,
    SCOPE_ADMIN_ORGUNIT_READONLY,
    SCOPE_ADMIN_ORGUNIT,
]

ALL_APP_SCOPES = AUTH_IDENTITY_SCOPES + APP_OPERATIONAL_SCOPES


FEATURE_SCOPE_MAP: dict[str, list[str]] = {
    "list_courses": [SCOPE_CLASSROOM_COURSES_READONLY],
    "sync_courses": [SCOPE_CLASSROOM_COURSES_READONLY],
    "list_roster": [SCOPE_CLASSROOM_ROSTERS_READONLY, SCOPE_CLASSROOM_PROFILE_EMAILS],
    "bulk_add_students": [SCOPE_CLASSROOM_ROSTERS],
    "add_teacher": [SCOPE_CLASSROOM_ROSTERS],
    "create_course": [SCOPE_CLASSROOM_COURSES],
    "archive_course": [SCOPE_CLASSROOM_COURSES],
    "delete_course": [SCOPE_CLASSROOM_COURSES],
    "remove_student": [SCOPE_CLASSROOM_ROSTERS],
    "remove_teacher": [SCOPE_CLASSROOM_ROSTERS],
    "create_invitation": [SCOPE_CLASSROOM_ROSTERS],
    "create_course_material": [SCOPE_CLASSROOM_COURSEWORK_MATERIALS],
    "create_class_announcement": [SCOPE_CLASSROOM_ANNOUNCEMENTS],
    "create_calendar_event": [SCOPE_CALENDAR],
    "import_google_sheet_preview": [SCOPE_SPREADSHEETS_READONLY],
    "list_groups": [SCOPE_ADMIN_GROUP_READONLY],
    "list_group_members": [SCOPE_ADMIN_GROUP_MEMBER_READONLY],
    "sync_groups": [SCOPE_ADMIN_GROUP_READONLY],
    "add_user_to_group": [SCOPE_ADMIN_GROUP_MEMBER],
    "remove_user_from_group": [SCOPE_ADMIN_GROUP_MEMBER],
    "list_directory_users": [SCOPE_ADMIN_USER_READONLY],
    "list_org_units": [SCOPE_ADMIN_ORGUNIT_READONLY],
    "move_user_org_unit": [SCOPE_ADMIN_ORGUNIT],
    "create_directory_user": [SCOPE_ADMIN_USER],
}


@dataclass(frozen=True)
class ScopeCheckResult:
    ok: bool
    missing: list[str]


class GoogleScopeMissingError(Exception):
    code = "GOOGLE_SCOPE_MISSING"

    def __init__(self, *, feature: str, missing_scopes: list[str], message: str | None = None):
        text = message or (
            f"Additional Google permission is required for '{feature}'. Reconnect Google to continue."
        )
        super().__init__(text)
        self.feature = feature
        self.missing_scopes = missing_scopes
        self.reconnect_flow = "google_reauthorize"

    def as_payload(self, reauthorize_url: str | None = None) -> dict:
        payload = {
            "code": self.code,
            "message": str(self),
            "feature": self.feature,
            "missingScopes": self.missing_scopes,
            "reconnectFlow": self.reconnect_flow,
        }
        if reauthorize_url:
            payload["reauthorizeUrl"] = reauthorize_url
        return payload


def normalize_scopes(scopes: Iterable[str] | str | None) -> list[str]:
    if scopes is None:
        return []
    raw = scopes.split() if isinstance(scopes, str) else list(scopes)
    cleaned = sorted({scope.strip() for scope in raw if isinstance(scope, str) and scope.strip()})
    return cleaned


def required_scopes_for_feature(feature: str) -> list[str]:
    return FEATURE_SCOPE_MAP.get(feature, [])


def validate_scopes(
    granted_scopes: Iterable[str] | str | None, required_scopes: Iterable[str] | None
) -> ScopeCheckResult:
    granted = set(normalize_scopes(granted_scopes))
    required = normalize_scopes(required_scopes)
    missing = [scope for scope in required if scope not in granted]
    return ScopeCheckResult(ok=len(missing) == 0, missing=missing)


def auth_scopes_for_request(mode: str = "default", upgrade_feature: str | None = None) -> list[str]:
    if mode == "upgrade" and upgrade_feature:
        return normalize_scopes(AUTH_IDENTITY_SCOPES + required_scopes_for_feature(upgrade_feature))
    if mode == "reconnect":
        return normalize_scopes(ALL_APP_SCOPES)
    return normalize_scopes(ALL_APP_SCOPES)

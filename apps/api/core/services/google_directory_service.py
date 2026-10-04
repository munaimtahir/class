"""Phase 2 Google Admin Directory service.

Uses the authenticated user's OAuth credentials with Directory API scopes.
The user must be a Google Workspace admin and have granted the required scopes.

Required OAuth scopes:
  https://www.googleapis.com/auth/admin.directory.group.readonly
  https://www.googleapis.com/auth/admin.directory.group.member
  https://www.googleapis.com/auth/admin.directory.group.member.readonly
"""

import logging
import json
from typing import Optional

from django.utils import timezone
from googleapiclient.errors import HttpError

from core.google_client import GoogleService
from core.models import DirectoryTarget, TargetType

logger = logging.getLogger(__name__)


class DirectoryServiceError(Exception):
    def __init__(self, message: str, code: str = "directory_error"):
        super().__init__(message)
        self.code = code


class GoogleDirectoryService:
    def __init__(self, user):
        self.user = user
        self._google = GoogleService(user)

    def _admin(self):
        return self._google.admin_directory()

    def _normalize_http_error(self, exc: HttpError, fallback: str = "directory_error") -> DirectoryServiceError:
        code = getattr(getattr(exc, "resp", None), "status", None)
        reason = ""
        message = ""
        try:
            payload = json.loads((getattr(exc, "content", b"") or b"").decode())
            error = payload.get("error") or {}
            message = error.get("message", "")
            errors = error.get("errors") or []
            if errors:
                reason = errors[0].get("reason", "")
        except (ValueError, TypeError, AttributeError):
            payload = {}

        if reason == "accessNotConfigured":
            return DirectoryServiceError(
                "Google Admin SDK API is not enabled for the configured Google Cloud project.",
                "api_not_enabled",
            )
        if code == 403 and (
            reason == "insufficientPermissions"
            or "insufficient authentication scopes" in message.lower()
        ):
            return DirectoryServiceError(
                "Google OAuth token is missing the required Admin SDK Directory scopes.",
                "insufficient_scopes",
            )
        if code == 404:
            return DirectoryServiceError("Resource not found in Google Directory.", "not_found")
        if code == 403:
            return DirectoryServiceError("Permission denied by Google Directory API.", "forbidden")
        if code == 409:
            return DirectoryServiceError("Conflict returned by Google Directory API.", "conflict")
        return DirectoryServiceError(str(exc), fallback)

    # ------------------------------------------------------------------
    # Groups
    # ------------------------------------------------------------------

    def list_groups(self, domain: Optional[str] = None) -> list[dict]:
        """List all Google Groups in the domain."""
        self._google.require_feature_scope("list_groups")
        try:
            service = self._admin()
            results = []
            page_token = None
            kwargs = {"customer": "my_customer", "maxResults": 200}
            if domain:
                kwargs["domain"] = domain
            while True:
                if page_token:
                    kwargs["pageToken"] = page_token
                resp = service.groups().list(**kwargs).execute()
                results.extend(resp.get("groups", []))
                page_token = resp.get("nextPageToken")
                if not page_token:
                    break
            return results
        except HttpError as exc:
            logger.error("list_groups failed: %s", exc)
            raise DirectoryServiceError(str(exc))

    def sync_groups_to_directory_targets(self, domain: Optional[str] = None) -> dict:
        """Fetch groups from Directory API and upsert into DirectoryTarget table."""
        groups = self.list_groups(domain=domain)
        created = updated = 0
        for g in groups:
            group_id = g.get("id", "")
            email = g.get("email", "")
            name = g.get("name", "")
            obj, was_created = DirectoryTarget.objects.update_or_create(
                target_type=TargetType.GROUP,
                external_id=group_id,
                defaults={
                    "email": email,
                    "display_name": name,
                    "metadata_json": {
                        "description": g.get("description", ""),
                        "directMembersCount": g.get("directMembersCount", 0),
                        "aliases": g.get("aliases", []),
                    },
                    "synced_at": timezone.now(),
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1
        return {"synced": len(groups), "created": created, "updated": updated}

    def list_group_members(self, group_email: str) -> list[dict]:
        """Return all members of a Google Group (expanded, no nested groups)."""
        self._google.require_feature_scope("list_group_members")
        try:
            service = self._admin()
            results = []
            page_token = None
            while True:
                kwargs = {"groupKey": group_email, "maxResults": 200}
                if page_token:
                    kwargs["pageToken"] = page_token
                resp = service.members().list(**kwargs).execute()
                for m in resp.get("members", []):
                    # Skip nested group entries — only keep user-type members
                    if m.get("type", "").upper() == "USER":
                        results.append(m)
                page_token = resp.get("nextPageToken")
                if not page_token:
                    break
            return results
        except HttpError as exc:
            logger.error("list_group_members(%s) failed: %s", group_email, exc)
            raise DirectoryServiceError(str(exc))

    def is_member_of_group(self, group_email: str, user_email: str) -> bool:
        """Check whether a user is already a member of the group."""
        self._google.require_feature_scope("list_group_members")
        try:
            service = self._admin()
            resp = service.members().hasMember(
                groupKey=group_email, memberKey=user_email
            ).execute()
            return resp.get("isMember", False)
        except HttpError as exc:
            if exc.resp.status == 404:
                return False
            raise DirectoryServiceError(str(exc))

    def add_member_to_group(self, group_email: str, user_email: str, role: str = "MEMBER") -> dict:
        """Add a user to a Google Group. Returns result dict."""
        self._google.require_feature_scope("add_user_to_group")
        if self.is_member_of_group(group_email, user_email):
            return {"skipped": True, "reason": "already_member", "email": user_email}
        try:
            service = self._admin()
            body = {"email": user_email, "role": role.upper()}
            result = service.members().insert(groupKey=group_email, body=body).execute()
            return {"success": True, "member": result}
        except HttpError as exc:
            logger.error("add_member_to_group(%s, %s) failed: %s", group_email, user_email, exc)
            raise DirectoryServiceError(str(exc))

    def remove_member_from_group(self, group_email: str, user_email: str) -> dict:
        """Remove a user from a Google Group."""
        self._google.require_feature_scope("remove_user_from_group")
        if not self.is_member_of_group(group_email, user_email):
            return {"skipped": True, "reason": "not_member", "email": user_email}
        try:
            service = self._admin()
            service.members().delete(groupKey=group_email, memberKey=user_email).execute()
            return {"success": True, "email": user_email}
        except HttpError as exc:
            logger.error("remove_member_from_group(%s, %s) failed: %s", group_email, user_email, exc)
            raise self._normalize_http_error(exc)

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------

    def iter_user_pages(self, query: str = "", max_results: Optional[int] = None):
        """Yield paginated Google Workspace user batches."""
        self._google.require_feature_scope("list_directory_users")
        try:
            service = self._admin()
            page_token = None
            remaining = max_results if max_results and max_results > 0 else None
            while True:
                chunk = min(remaining, 500) if remaining is not None else 500
                kwargs = {
                    "customer": "my_customer",
                    "maxResults": chunk,
                    "orderBy": "email",
                }
                if query:
                    kwargs["query"] = query
                if page_token:
                    kwargs["pageToken"] = page_token
                resp = service.users().list(**kwargs).execute()
                batch = resp.get("users", [])
                yield batch
                if remaining is not None:
                    remaining -= len(batch)
                    if remaining <= 0:
                        break
                page_token = resp.get("nextPageToken")
                if not page_token or not batch:
                    break
        except HttpError as exc:
            logger.error("iter_user_pages failed: %s", exc)
            raise self._normalize_http_error(exc)

    def list_users(self, query: str = "", max_results: Optional[int] = None) -> list[dict]:
        """List Google Workspace users."""
        users: list[dict] = []
        for batch in self.iter_user_pages(query=query, max_results=max_results):
            users.extend(batch)
        return users

    def get_user(self, user_key: str) -> dict:
        self._google.require_feature_scope("list_directory_users")
        try:
            return self._admin().users().get(userKey=user_key).execute()
        except HttpError as exc:
            logger.error("get_user(%s) failed: %s", user_key, exc)
            raise self._normalize_http_error(exc)

    def move_user_to_org_unit(self, user_key: str, org_unit_path: str) -> dict:
        self._google.require_feature_scope("move_user_org_unit")
        try:
            body = {"orgUnitPath": org_unit_path}
            updated = self._admin().users().update(userKey=user_key, body=body).execute()
            return {"success": True, "user": updated}
        except HttpError as exc:
            logger.error("move_user_to_org_unit(%s, %s) failed: %s", user_key, org_unit_path, exc)
            raise self._normalize_http_error(exc)

    def create_user(
        self,
        primary_email: str,
        given_name: str,
        family_name: str,
        password: str,
        org_unit_path: str,
        change_password_at_next_login: bool = True,
    ) -> dict:
        self._google.require_feature_scope("create_directory_user")
        try:
            body = {
                "primaryEmail": primary_email,
                "name": {
                    "givenName": given_name or primary_email.split("@")[0],
                    "familyName": family_name or "User",
                },
                "password": password,
                "changePasswordAtNextLogin": change_password_at_next_login,
                "orgUnitPath": org_unit_path,
            }
            created = self._admin().users().insert(body=body).execute()
            return {"success": True, "user": created}
        except HttpError as exc:
            logger.error("create_user(%s) failed: %s", primary_email, exc)
            raise self._normalize_http_error(exc)

    # ------------------------------------------------------------------
    # Org units
    # ------------------------------------------------------------------

    def list_org_units(self) -> list[dict]:
        self._google.require_feature_scope("list_org_units")
        try:
            service = self._admin()
            resp = service.orgunits().list(customerId="my_customer", type="all").execute()
            return resp.get("organizationUnits", [])
        except HttpError as exc:
            logger.error("list_org_units failed: %s", exc)
            raise self._normalize_http_error(exc)

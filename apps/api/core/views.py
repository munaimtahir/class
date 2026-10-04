import logging
import urllib.parse
from datetime import datetime

import requests
from django.conf import settings
from django.contrib.auth import get_user_model, login, logout
from django.db import transaction
from django.shortcuts import redirect
from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from .google_client import GoogleService, GoogleServiceError
from .google_scopes import GoogleScopeMissingError, auth_scopes_for_request, normalize_scopes
from .imports.service import FileImportService, GoogleSheetImportService, ImportServiceError
from .models import Course, ImportBatch, PostLog, Session
from .publish.message_renderer import CombinedDayMessageRenderer
from .serializers import (
    CourseSerializer,
    ImportBatchListSerializer,
    ImportBatchSerializer,
    PostLogSerializer,
    SessionSerializer,
    UserSerializer,
)
from .tasks import create_classroom_post, generate_meet_link

User = get_user_model()
logger = logging.getLogger(__name__)


def _reauthorize_url(request, feature: str = "") -> str:
    upgrade_query = f"&upgrade={urllib.parse.quote(feature)}" if feature else ""
    return f"/api/auth/google/start?mode=upgrade{upgrade_query}"


def _scope_missing_response(request, exc: GoogleScopeMissingError):
    return Response(
        exc.as_payload(reauthorize_url=_reauthorize_url(request, exc.feature)),
        status=403,
    )


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def google_auth_start(request):
    mode = (request.query_params.get("mode") or "default").strip().lower()
    upgrade_feature = (request.query_params.get("upgrade") or "").strip()
    if mode not in {"default", "reconnect", "upgrade"}:
        return Response({"detail": "Invalid mode.", "code": "invalid_mode"}, status=400)

    requested_scopes = auth_scopes_for_request(mode=mode, upgrade_feature=upgrade_feature)

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(requested_scopes),
        "access_type": "offline",
        "include_granted_scopes": "true",
        "prompt": "consent",
    }
    return Response(
        {
            "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params),
            "mode": mode,
            "upgrade_feature": upgrade_feature or None,
            "requested_scopes": requested_scopes,
        }
    )


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def google_auth_callback(request):
    code = request.query_params.get("code")
    if not code:
        return Response({"detail": "Missing code"}, status=400)

    token_resp = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        },
        timeout=15,
    )
    if token_resp.status_code != 200:
        return Response({"detail": "Google token exchange failed"}, status=400)
    token_data = token_resp.json()
    access_token = token_data.get("access_token")
    if not access_token:
        return Response({"detail": "Google access token missing"}, status=400)
    granted_scopes = normalize_scopes(token_data.get("scope", ""))

    user_info_resp = requests.get(
        "https://openidconnect.googleapis.com/v1/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15,
    )
    if user_info_resp.status_code != 200:
        return Response({"detail": "Unable to fetch Google profile"}, status=400)
    profile = user_info_resp.json()
    if not profile.get("email"):
        return Response({"detail": "Google profile email missing"}, status=400)

    with transaction.atomic():
        user, _ = User.objects.select_for_update().update_or_create(
            email=profile.get("email", ""),
            defaults={
                "name": profile.get("name", ""),
                "google_id": profile.get("sub", ""),
                "google_scopes": " ".join(granted_scopes),
                "google_scopes_json": granted_scopes,
                "access_token": access_token,
                "token_meta_json": {
                    "scope": token_data.get("scope", ""),
                    "expires_in": token_data.get("expires_in"),
                    "token_type": token_data.get("token_type"),
                    "id_token_present": bool(token_data.get("id_token")),
                },
                "google_last_refresh_at": timezone.now(),
            },
        )
        if token_data.get("refresh_token"):
            user.set_refresh_token(token_data["refresh_token"])
            user.token_meta_json["refresh_token_rotated"] = True
        user.save()
    logger.info("Google OAuth granted scopes for %s: %s", user.email, " ".join(granted_scopes))

    login(request, user)
    return redirect(settings.FRONTEND_URL)


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def auth_status(request):
    if not request.user.is_authenticated:
        return Response({"authenticated": False})
    return Response(
        {
            "authenticated": True,
            "user": UserSerializer(request.user).data,
            "granted_scopes": normalize_scopes(
                request.user.google_scopes_json or request.user.google_scopes
            ),
            "google_last_refresh_at": request.user.google_last_refresh_at,
        }
    )


@api_view(["POST"])
def auth_logout(request):
    logout(request)
    return Response({"ok": True})


class CourseViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CourseSerializer

    def get_queryset(self):
        return Course.objects.filter(user=self.request.user)

    @action(detail=False, methods=["get"], url_path="sync")
    def sync(self, request):
        google = GoogleService(request.user)
        try:
            courses = google.list_courses()
        except GoogleScopeMissingError as exc:
            return _scope_missing_response(request, exc)
        except GoogleServiceError as exc:
            return Response({"detail": str(exc), "code": exc.code}, status=400)
        created = 0
        for c in courses:
            _, was_created = Course.objects.update_or_create(
                user=request.user,
                google_course_id=c.get("id", ""),
                defaults={
                    "name": c.get("name", ""),
                    "section": c.get("section", ""),
                },
            )
            if was_created:
                created += 1
        return Response({"synced": len(courses), "created": created})


class SessionViewSet(viewsets.ModelViewSet):
    serializer_class = SessionSerializer

    def get_queryset(self):
        return Session.objects.filter(course__user=self.request.user).select_related("course", "meet_event")

    def perform_create(self, serializer):
        course = serializer.validated_data["course"]
        if course.user_id != self.request.user.id:
            raise permissions.PermissionDenied("Course ownership mismatch")
        serializer.save()

    def perform_update(self, serializer):
        course = serializer.validated_data.get("course", serializer.instance.course)
        if course.user_id != self.request.user.id:
            raise permissions.PermissionDenied("Course ownership mismatch")
        serializer.save()

    @action(detail=False, methods=["post"], url_path="generate-meet")
    def generate_meet(self, request):
        ids = request.data.get("session_ids", [])
        sessions = Session.objects.filter(id__in=ids, course__user=request.user)
        session_ids = list(sessions.values_list("id", flat=True))
        for sid in session_ids:
            generate_meet_link.delay(sid)
        return Response({"queued": len(session_ids)})

    @action(detail=False, methods=["post"], url_path="schedule-posts")
    def schedule_posts(self, request):
        ids = request.data.get("session_ids", [])
        for sid in ids:
            session = Session.objects.get(id=sid, course__user=request.user)
            eta = timezone.make_aware(datetime.combine(session.date, session.start_time))
            create_classroom_post.apply_async(args=[sid, False], eta=eta)
        return Response({"scheduled": len(ids)})

    @action(detail=False, methods=["post"], url_path="publish-now")
    def publish_now(self, request):
        ids = request.data.get("session_ids", [])
        for sid in ids:
            create_classroom_post.delay(sid, True)
        return Response({"queued": len(ids)})


class LogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PostLogSerializer

    def get_queryset(self):
        return PostLog.objects.filter(session__course__user=self.request.user).select_related("session")


# ---------------------------------------------------------------------------
# Google Sheet import views
# ---------------------------------------------------------------------------

@api_view(["POST"])
def import_google_sheet_preview(request):
    """
    Parse and validate a Google Sheet without writing to the database.

    Returns a preview payload including:
    - parsed session rows with status (valid / invalid / duplicate)
    - a preview_token for use with the commit endpoint
    - summary counts
    """
    service = GoogleSheetImportService(request.user)
    try:
        result = service.preview(
            sheet_url=request.data.get("sheet_url", ""),
            target_day=request.data.get("target_day"),
            target_date=request.data.get("target_date"),
            sheet_name=request.data.get("sheet_name"),
            default_course_map_id=request.data.get("default_course_map_id"),
        )
    except GoogleScopeMissingError as exc:
        return _scope_missing_response(request, exc)
    except ImportServiceError as exc:
        return Response({"detail": str(exc), "code": exc.code}, status=400)
    return Response(result)


@api_view(["POST"])
def import_file_preview(request):
    """Parse and validate an uploaded CSV/TSV file without writing to the database."""
    uploaded = request.FILES.get("file")
    if uploaded is None:
        return Response({"detail": "file is required."}, status=400)

    service = FileImportService(request.user)
    try:
        result = service.preview(
            file_name=uploaded.name,
            file_bytes=uploaded.read(),
            target_day=request.data.get("target_day"),
            target_date=request.data.get("target_date"),
            default_course_map_id=request.data.get("default_course_map_id"),
        )
    except GoogleScopeMissingError as exc:
        return _scope_missing_response(request, exc)
    except ImportServiceError as exc:
        return Response({"detail": str(exc), "code": exc.code}, status=400)
    return Response(result)


@api_view(["POST"])
def import_google_sheet_commit(request):
    """
    Commit a previewed import: create ImportBatch + SessionDraft records.

    Request body:
        preview_token (required)
        accepted_row_indices (optional list of row_index ints to limit which rows are committed)
    """
    preview_token = request.data.get("preview_token", "").strip()
    if not preview_token:
        return Response({"detail": "preview_token is required."}, status=400)

    service = GoogleSheetImportService(request.user)
    try:
        result = service.commit(
            preview_token=preview_token,
            accepted_row_indices=request.data.get("accepted_row_indices"),
        )
    except ImportServiceError as exc:
        return Response({"detail": str(exc), "code": exc.code}, status=400)
    return Response(result, status=201)


@api_view(["POST"])
def promote_import_batch(request, batch_id):
    """
    Promote all accepted SessionDraft records in a batch to live Session records.

    The created sessions are in status='pending', ready for the publish pipeline.
    """
    service = GoogleSheetImportService(request.user)
    try:
        result = service.promote_batch(batch_id)
    except ImportServiceError as exc:
        return Response({"detail": str(exc), "code": exc.code}, status=400)
    return Response(result)


@api_view(["GET"])
def list_import_batches(request):
    """List all import batches belonging to the authenticated user."""
    batches = ImportBatch.objects.filter(user=request.user).order_by("-created_at")
    return Response(ImportBatchListSerializer(batches, many=True).data)


@api_view(["GET"])
def get_import_batch(request, batch_id):
    """Return a single import batch with its session drafts."""
    try:
        batch = ImportBatch.objects.get(id=batch_id, user=request.user)
    except ImportBatch.DoesNotExist:
        return Response({"detail": "Import batch not found."}, status=404)
    return Response(ImportBatchSerializer(batch).data)


# ---------------------------------------------------------------------------
# Combined-day message endpoints
# ---------------------------------------------------------------------------


@api_view(["POST"])
def combined_day_preview(request):
    """Generate a preview of the combined-day message without posting.

    Request body::

        {
            "session_ids": [1, 2, 3],
            "template": "single_day_combined_message",
            "options": {
                "include_year": false,
                "include_video_label": true,
                "sort_by_time": true,
                "include_day_heading": false
            }
        }
    """
    template = request.data.get("template", "single_day_combined_message")
    if template != "single_day_combined_message":
        return Response({"detail": f"Unsupported template: {template}"}, status=400)

    session_ids = request.data.get("session_ids", [])
    sessions = (
        Session.objects.filter(id__in=session_ids, course__user=request.user)
        .select_related("course", "meet_event")
    )
    if not sessions.exists():
        return Response({"detail": "No sessions found for the given IDs."}, status=400)

    renderer = CombinedDayMessageRenderer()
    result = renderer.render(list(sessions), request.data.get("options"))
    return Response(result)


@api_view(["POST"])
def combined_day_publish(request):
    """Render and publish one combined-day announcement to Google Classroom.

    Request body::

        {
            "session_ids": [1, 2, 3],
            "course_id": "<google_course_id>",
            "template": "single_day_combined_message",
            "options": { ... }
        }
    """
    template = request.data.get("template", "single_day_combined_message")
    if template != "single_day_combined_message":
        return Response({"detail": f"Unsupported template: {template}"}, status=400)

    course_id = (request.data.get("course_id") or "").strip()
    if not course_id:
        return Response({"detail": "course_id is required."}, status=400)

    session_ids = request.data.get("session_ids", [])
    sessions = (
        Session.objects.filter(id__in=session_ids, course__user=request.user)
        .select_related("course", "meet_event")
    )
    if not sessions.exists():
        return Response({"detail": "No sessions found for the given IDs."}, status=400)

    renderer = CombinedDayMessageRenderer()
    result = renderer.render(list(sessions), request.data.get("options"))
    message = result.get("message", "")
    if not message:
        return Response({"detail": "Rendered message is empty — nothing to publish."}, status=400)

    google = GoogleService(request.user)
    try:
        post_id = google.create_classroom_announcement(course_id, message)
    except GoogleScopeMissingError as exc:
        return _scope_missing_response(request, exc)
    except GoogleServiceError as exc:
        return Response({"detail": str(exc), "code": exc.code}, status=400)

    for session in sessions:
        PostLog.objects.create(
            session=session,
            status=Session.STATUS_POSTED,
            message=f"Published via single_day_combined_message (announcement {post_id})",
        )

    return Response(
        {
            "google_post_id": post_id,
            "posting_mode": "single_day_combined_message",
            "session_count": result["session_count"],
            "message_length": len(message),
        },
        status=201,
    )

from rest_framework import serializers

from .models import ClassroomPost, Course, ImportBatch, MeetEvent, PostLog, Session, SessionDraft, User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "name", "google_id", "role"]


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ["id", "google_course_id", "name", "section"]


class SessionSerializer(serializers.ModelSerializer):
    meet_link = serializers.SerializerMethodField()
    calendar_event_id = serializers.SerializerMethodField()

    def get_meet_link(self, obj):
        meet_event = getattr(obj, "meet_event", None)
        return getattr(meet_event, "meet_link", "")

    def get_calendar_event_id(self, obj):
        meet_event = getattr(obj, "meet_event", None)
        return getattr(meet_event, "calendar_event_id", "")

    class Meta:
        model = Session
        fields = [
            "id",
            "course",
            "date",
            "start_time",
            "end_time",
            "title",
            "topic",
            "subject",
            "group",
            "meet_required",
            "post_type",
            "status",
            "meet_link",
            "calendar_event_id",
        ]


class MeetEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeetEvent
        fields = ["id", "session", "calendar_event_id", "meet_link"]


class ClassroomPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClassroomPost
        fields = ["id", "session", "google_post_id", "scheduled_time", "status"]


class PostLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostLog
        fields = ["id", "session", "status", "message", "created_at"]


class SessionDraftSerializer(serializers.ModelSerializer):
    course_name = serializers.SerializerMethodField()

    def get_course_name(self, obj):
        return obj.course.name if obj.course else None

    class Meta:
        model = SessionDraft
        fields = [
            "id",
            "row_index",
            "date",
            "start_time",
            "end_time",
            "title",
            "subject",
            "topic",
            "subgroup_label",
            "requires_meet",
            "publish_mode",
            "scheduled_for",
            "topic_label",
            "notes",
            "dedupe_hash",
            "status",
            "validation_errors_json",
            "course",
            "course_name",
            "promoted_session",
            "created_at",
        ]


class ImportBatchSerializer(serializers.ModelSerializer):
    session_drafts = SessionDraftSerializer(many=True, read_only=True)

    class Meta:
        model = ImportBatch
        fields = [
            "id",
            "source_type",
            "source_ref",
            "spreadsheet_id",
            "sheet_name",
            "target_date",
            "row_count",
            "valid_count",
            "invalid_count",
            "duplicate_count",
            "status",
            "diagnostics_json",
            "created_at",
            "session_drafts",
        ]


class ImportBatchListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for the batch list view (no nested drafts)."""

    class Meta:
        model = ImportBatch
        fields = [
            "id",
            "source_type",
            "source_ref",
            "spreadsheet_id",
            "sheet_name",
            "target_date",
            "row_count",
            "valid_count",
            "invalid_count",
            "duplicate_count",
            "status",
            "created_at",
        ]


# ---------------------------------------------------------------------------
# Phase 2 — Serializers
# ---------------------------------------------------------------------------

from .models import CommandJob, CommandJobItem, DirectoryTarget, OnboardingBundle


class DirectoryTargetSerializer(serializers.ModelSerializer):
    class Meta:
        model = DirectoryTarget
        fields = [
            "id", "target_type", "external_id", "email", "display_name",
            "metadata_json", "synced_at", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "synced_at", "created_at", "updated_at"]


class OnboardingBundleSerializer(serializers.ModelSerializer):
    created_by_email = serializers.SerializerMethodField()

    def get_created_by_email(self, obj):
        return obj.created_by.email if obj.created_by else None

    class Meta:
        model = OnboardingBundle
        fields = [
            "id", "name", "role_type", "groups_json", "classroom_courses_json",
            "description", "active", "created_by", "created_by_email",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_by_email", "created_at", "updated_at"]


class CommandJobItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommandJobItem
        fields = [
            "id", "command_job", "target_type", "target_ref", "action",
            "payload_json", "status", "result_json", "retry_count",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class CommandJobSerializer(serializers.ModelSerializer):
    created_by_email = serializers.SerializerMethodField()
    items = CommandJobItemSerializer(many=True, read_only=True)
    item_count = serializers.SerializerMethodField()

    def get_created_by_email(self, obj):
        return obj.created_by.email if obj.created_by else None

    def get_item_count(self, obj):
        return obj.items.count()

    class Meta:
        model = CommandJob
        fields = [
            "id", "job_type", "created_by", "created_by_email", "status",
            "dry_run", "target_summary_json", "result_summary_json",
            "scheduled_for", "item_count", "items", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "created_by", "created_by_email", "status",
            "result_summary_json", "item_count", "items", "created_at", "updated_at",
        ]


class CommandJobListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for job list (no nested items)."""
    created_by_email = serializers.SerializerMethodField()
    item_count = serializers.SerializerMethodField()

    def get_created_by_email(self, obj):
        return obj.created_by.email if obj.created_by else None

    def get_item_count(self, obj):
        return obj.items.count()

    class Meta:
        model = CommandJob
        fields = [
            "id", "job_type", "created_by_email", "status", "dry_run",
            "target_summary_json", "result_summary_json", "item_count",
            "scheduled_for", "created_at", "updated_at",
        ]


# ---------------------------------------------------------------------------
# Phase 2B — Classroom Lifecycle + Direct Removal serializers
# ---------------------------------------------------------------------------

class CreateCourseSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    section = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    description_heading = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    description = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")
    room = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    owner_id = serializers.CharField(max_length=255, required=False, allow_blank=True, default="me")


class CourseIdSerializer(serializers.Serializer):
    course_id = serializers.CharField(max_length=255)


class RemoveStudentSerializer(serializers.Serializer):
    course_id = serializers.CharField(max_length=255)
    student_email = serializers.EmailField()


class RemoveTeacherSerializer(serializers.Serializer):
    course_id = serializers.CharField(max_length=255)
    teacher_email = serializers.EmailField()


class PreflightRequestSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=[
        "create_course", "archive_course", "delete_course",
        "remove_student", "remove_teacher",
    ])
    course_id = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    name = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    student_email = serializers.EmailField(required=False, allow_blank=True, default="")
    teacher_email = serializers.EmailField(required=False, allow_blank=True, default="")

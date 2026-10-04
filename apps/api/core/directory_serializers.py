from rest_framework import serializers

from .models import (
    ApprovalRequest,
    DirectoryAuditLog,
    DirectoryChangeJob,
    DirectoryChangeJobItem,
    DirectoryIssue,
    DirectorySyncJob,
    DirectoryUser,
    DirectoryVerifyJob,
    DirectoryVerifyRow,
    EmailTemplateRule,
    OrgUnitTemplate,
    ProvisioningRecord,
)


class DirectoryUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = DirectoryUser
        fields = [
            "id",
            "google_user_id",
            "primary_email",
            "full_name",
            "given_name",
            "family_name",
            "org_unit_path",
            "user_category",
            "external_identifier",
            "roll_number",
            "employee_id",
            "department",
            "program",
            "batch",
            "year",
            "suspended",
            "archived",
            "last_synced_at",
            "sync_source",
            "expected_org_unit_path",
            "expected_email_valid",
            "aliases_json",
            "phones_json",
            "normalized_email",
            "normalized_full_name",
            "normalized_phone",
            "is_active",
            "last_seen_at",
            "metadata_json",
            "created_at",
            "updated_at",
        ]


class DirectoryUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DirectoryUser
        fields = [
            "user_category",
            "external_identifier",
            "roll_number",
            "employee_id",
            "department",
            "program",
            "batch",
            "year",
            "metadata_json",
        ]


class OrgUnitTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrgUnitTemplate
        fields = [
            "id",
            "name",
            "user_category",
            "department",
            "program",
            "batch",
            "year",
            "target_org_unit_path",
            "priority",
            "rule_config_json",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class EmailTemplateRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailTemplateRule
        fields = [
            "id",
            "name",
            "user_category",
            "department",
            "program",
            "batch",
            "year",
            "email_pattern",
            "domain",
            "collision_strategy",
            "normalization_rules",
            "priority",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class DirectoryIssueSerializer(serializers.ModelSerializer):
    directory_user_email = serializers.SerializerMethodField()
    reviewed_by_email = serializers.SerializerMethodField()

    def get_directory_user_email(self, obj):
        return obj.directory_user.primary_email if obj.directory_user else None

    def get_reviewed_by_email(self, obj):
        return obj.reviewed_by.email if obj.reviewed_by else None

    class Meta:
        model = DirectoryIssue
        fields = [
            "id",
            "directory_user",
            "directory_user_email",
            "issue_type",
            "severity",
            "actual_value",
            "expected_value",
            "suggested_action",
            "status",
            "detected_at",
            "reviewed_by",
            "reviewed_by_email",
            "reviewed_at",
            "applied_at",
            "failure_reason",
            "metadata_json",
            "created_at",
            "updated_at",
        ]


class DirectoryChangeJobItemSerializer(serializers.ModelSerializer):
    directory_user_email = serializers.SerializerMethodField()

    def get_directory_user_email(self, obj):
        return obj.directory_user.primary_email if obj.directory_user else None

    class Meta:
        model = DirectoryChangeJobItem
        fields = [
            "id",
            "directory_user",
            "directory_user_email",
            "issue",
            "target_ref",
            "action",
            "before_value",
            "after_value",
            "payload_json",
            "status",
            "result_json",
            "error_text",
            "created_at",
            "updated_at",
        ]


class DirectoryChangeJobSerializer(serializers.ModelSerializer):
    items = DirectoryChangeJobItemSerializer(many=True, read_only=True)
    initiated_by_email = serializers.SerializerMethodField()
    approved_by_email = serializers.SerializerMethodField()
    item_count = serializers.SerializerMethodField()

    def get_initiated_by_email(self, obj):
        return obj.initiated_by.email if obj.initiated_by else None

    def get_approved_by_email(self, obj):
        return obj.approved_by.email if obj.approved_by else None

    def get_item_count(self, obj):
        return obj.items.count()

    class Meta:
        model = DirectoryChangeJob
        fields = [
            "id",
            "job_type",
            "scope_type",
            "initiated_by",
            "initiated_by_email",
            "approved_by",
            "approved_by_email",
            "preview_of",
            "is_dry_run",
            "requires_admin_approval",
            "input_payload",
            "preview_summary",
            "execution_summary",
            "status",
            "approved_at",
            "started_at",
            "finished_at",
            "failure_reason",
            "item_count",
            "items",
            "created_at",
            "updated_at",
        ]


class ProvisioningRecordSerializer(serializers.ModelSerializer):
    created_by_email = serializers.SerializerMethodField()

    def get_created_by_email(self, obj):
        return obj.created_by.email if obj.created_by else None

    class Meta:
        model = ProvisioningRecord
        fields = [
            "id",
            "full_name",
            "given_name",
            "family_name",
            "user_category",
            "source_identifier",
            "generated_email",
            "target_org_unit_path",
            "temp_password_policy",
            "provisioning_mode",
            "status",
            "google_user_id",
            "preview_payload",
            "execution_payload",
            "failure_reason",
            "created_by",
            "created_by_email",
            "approved_by",
            "change_job",
            "created_at",
            "updated_at",
        ]


class DirectoryAuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.SerializerMethodField()

    def get_actor_email(self, obj):
        return obj.actor.email if obj.actor else None

    class Meta:
        model = DirectoryAuditLog
        fields = [
            "id",
            "actor",
            "actor_email",
            "approval_request",
            "linked_change_job",
            "linked_provisioning_record",
            "action_type",
            "target_type",
            "target_ref",
            "is_dry_run",
            "success",
            "before_json",
            "after_json",
            "request_json",
            "response_json",
            "error_message",
            "external_reference",
            "correlation_id",
            "created_at",
        ]


class ApprovalRequestSerializer(serializers.ModelSerializer):
    requested_by_email = serializers.SerializerMethodField()
    reviewed_by_email = serializers.SerializerMethodField()

    def get_requested_by_email(self, obj):
        return obj.requested_by.email if obj.requested_by else None

    def get_reviewed_by_email(self, obj):
        return obj.reviewed_by.email if obj.reviewed_by else None

    class Meta:
        model = ApprovalRequest
        fields = [
            "id",
            "action_type",
            "target_type",
            "target_reference",
            "payload",
            "requested_by",
            "requested_by_email",
            "requested_at",
            "status",
            "reviewed_by",
            "reviewed_by_email",
            "reviewed_at",
            "review_notes",
            "linked_change_job",
            "linked_provisioning_record",
            "execution_status",
            "execution_message",
            "created_at",
            "updated_at",
        ]


class ApprovalRequestCreateSerializer(serializers.Serializer):
    action_type = serializers.CharField(max_length=100)
    target_type = serializers.CharField(max_length=50)
    target_reference = serializers.CharField(max_length=255)
    payload = serializers.JSONField(required=False, default=dict)
    linked_change_job_id = serializers.IntegerField(required=False, min_value=1)
    linked_provisioning_record_id = serializers.IntegerField(required=False, min_value=1)


class ApprovalReviewSerializer(serializers.Serializer):
    review_notes = serializers.CharField(required=False, allow_blank=True, default="")


class DirectorySyncRequestSerializer(serializers.Serializer):
    query = serializers.CharField(required=False, allow_blank=True, default="")
    max_results = serializers.IntegerField(required=False, min_value=1, max_value=50000, allow_null=True)


class DirectorySyncJobSerializer(serializers.ModelSerializer):
    started_by_email = serializers.SerializerMethodField()

    def get_started_by_email(self, obj):
        return obj.started_by.email if obj.started_by else None

    class Meta:
        model = DirectorySyncJob
        fields = [
            "id",
            "started_by",
            "started_by_email",
            "status",
            "query",
            "max_results",
            "started_at",
            "completed_at",
            "pages_fetched",
            "users_fetched_total",
            "users_upserted_total",
            "users_created_total",
            "users_updated_total",
            "error_message",
            "result_summary_json",
            "created_at",
            "updated_at",
        ]


class DirectoryVerifyJobSerializer(serializers.ModelSerializer):
    created_by_email = serializers.SerializerMethodField()

    def get_created_by_email(self, obj):
        return obj.created_by.email if obj.created_by else None

    class Meta:
        model = DirectoryVerifyJob
        fields = [
            "id",
            "created_by",
            "created_by_email",
            "source_filename",
            "source_type",
            "sheet_name",
            "status",
            "row_count",
            "summary_json",
            "column_mapping_json",
            "error_message",
            "created_at",
            "completed_at",
            "updated_at",
        ]


class DirectoryVerifyRowSerializer(serializers.ModelSerializer):
    matched_directory_user_email = serializers.SerializerMethodField()

    def get_matched_directory_user_email(self, obj):
        return obj.matched_directory_user.primary_email if obj.matched_directory_user else None

    class Meta:
        model = DirectoryVerifyRow
        fields = [
            "id",
            "job",
            "row_no",
            "input_json",
            "matched_directory_user",
            "matched_directory_user_email",
            "matched_email",
            "matched_name",
            "match_basis",
            "verdict",
            "confidence_score",
            "notes",
            "created_at",
        ]


class IssueScanRequestSerializer(serializers.Serializer):
    user_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), required=False, allow_empty=True
    )


class IssueActionSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, default="")


class BulkIssueApproveSerializer(serializers.Serializer):
    issue_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), allow_empty=False)
    note = serializers.CharField(required=False, allow_blank=True, default="")


class ChangeJobPreviewRequestSerializer(serializers.Serializer):
    job_type = serializers.CharField()
    scope_type = serializers.CharField(default="issue_selection")
    issue_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), required=False, allow_empty=True
    )
    user_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), required=False, allow_empty=True
    )
    target_org_unit_path = serializers.CharField(required=False, allow_blank=True, default="")
    input_payload = serializers.JSONField(required=False, default=dict)


class ChangeJobExecuteRequestSerializer(serializers.Serializer):
    preview_job_id = serializers.IntegerField(min_value=1)
    dry_run = serializers.BooleanField(required=False, default=False)
    approval_request_id = serializers.IntegerField(required=False, min_value=1)


class ProvisioningPreviewRequestSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255)
    given_name = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    family_name = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    user_category = serializers.CharField(max_length=20)
    source_identifier = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    department = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    program = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    batch = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    year = serializers.CharField(max_length=50, required=False, allow_blank=True, default="")
    temp_password_policy = serializers.CharField(max_length=100, required=False, allow_blank=True, default="change_on_first_login")


class ProvisioningCreateRequestSerializer(serializers.Serializer):
    preview_record_id = serializers.IntegerField(required=False, min_value=1)
    payload = ProvisioningPreviewRequestSerializer(required=False)


class BulkProvisioningPreviewRequestSerializer(serializers.Serializer):
    rows = serializers.ListField(
        child=ProvisioningPreviewRequestSerializer(), allow_empty=False
    )


class BulkProvisioningCreateRequestSerializer(serializers.Serializer):
    preview_record_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), allow_empty=False)
    approval_request_id = serializers.IntegerField(required=False, min_value=1)

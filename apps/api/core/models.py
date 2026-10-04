from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ImproperlyConfigured
from django.db import models

from .managers import UserManager


# ---------------------------------------------------------------------------
# Phase 2 — Enums / Constants
# ---------------------------------------------------------------------------

class JobStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    RUNNING = "running", "Running"
    COMPLETED = "completed", "Completed"
    PARTIAL = "partial", "Partial"
    FAILED = "failed", "Failed"
    DRY_RUN = "dry_run", "Dry Run"


class ItemStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    SUCCESS = "success", "Success"
    SKIPPED = "skipped", "Skipped"
    FAILED = "failed", "Failed"
    RETRYING = "retrying", "Retrying"


class TargetType(models.TextChoices):
    GROUP = "group", "Google Group"
    USER = "user", "User"
    COURSE = "course", "Classroom Course"


class ActionType(models.TextChoices):
    ADD_USER_TO_GROUP = "ADD_USER_TO_GROUP", "Add User to Group"
    REMOVE_USER_FROM_GROUP = "REMOVE_USER_FROM_GROUP", "Remove User from Group"
    ADD_STUDENT_TO_COURSE = "ADD_STUDENT_TO_COURSE", "Add Student to Course"
    ADD_TEACHER_TO_COURSE = "ADD_TEACHER_TO_COURSE", "Add Teacher to Course"
    ENROLL_GROUP_TO_COURSE = "ENROLL_GROUP_TO_COURSE", "Enroll Group to Course"
    APPLY_ONBOARDING_BUNDLE = "APPLY_ONBOARDING_BUNDLE", "Apply Onboarding Bundle"
    BULK_CSV_ONBOARDING = "BULK_CSV_ONBOARDING", "Bulk CSV Onboarding"
    # Phase 2B — Classroom lifecycle + direct removal
    CREATE_COURSE = "CREATE_COURSE", "Create Course"
    ARCHIVE_COURSE = "ARCHIVE_COURSE", "Archive Course"
    DELETE_COURSE = "DELETE_COURSE", "Delete Course"
    REMOVE_STUDENT_FROM_COURSE = "REMOVE_STUDENT_FROM_COURSE", "Remove Student from Course"
    REMOVE_TEACHER_FROM_COURSE = "REMOVE_TEACHER_FROM_COURSE", "Remove Teacher from Course"


class RoleType(models.TextChoices):
    STUDENT = "student", "Student"
    TEACHER = "teacher", "Teacher"
    MEMBER = "member", "Member"


class UserRole(models.TextChoices):
    VIEWER = "viewer", "Viewer"
    OPERATOR = "operator", "Operator"
    ADMIN = "admin", "Admin"


class DirectoryUserCategory(models.TextChoices):
    STUDENT = "student", "Student"
    FACULTY = "faculty", "Faculty"
    STAFF = "staff", "Staff"
    OTHER = "other", "Other"


class IssueSeverity(models.TextChoices):
    CRITICAL = "critical", "Critical"
    WARNING = "warning", "Warning"
    INFO = "info", "Info"


class DirectoryIssueStatus(models.TextChoices):
    DETECTED = "detected", "Detected"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    EXCEPTION_MARKED = "exception_marked", "Exception Marked"
    APPLIED = "applied", "Applied"
    FAILED = "failed", "Failed"


class DirectoryIssueType(models.TextChoices):
    INVALID_ORG_UNIT = "invalid_org_unit", "Invalid Org Unit"
    INVALID_EMAIL_PATTERN = "invalid_email_pattern", "Invalid Email Pattern"
    MISSING_REQUIRED_IDENTIFIER = "missing_required_identifier", "Missing Required Identifier"
    LIKELY_DUPLICATE_CONFLICT = "likely_duplicate_conflict", "Likely Duplicate Conflict"
    USER_CATEGORY_MISMATCH = "user_category_mismatch", "User Category Mismatch"
    TEMPLATE_RESOLUTION_FAILURE = "template_resolution_failure", "Template Resolution Failure"


class DirectorySyncJobStatus(models.TextChoices):
    QUEUED = "queued", "Queued"
    RUNNING = "running", "Running"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class DirectoryVerifyJobStatus(models.TextChoices):
    UPLOADED = "uploaded", "Uploaded"
    PROCESSING = "processing", "Processing"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class DirectoryVerifyVerdict(models.TextChoices):
    EXISTS = "exists", "Exists"
    DOES_NOT_EXIST = "does_not_exist", "Does Not Exist"
    AMBIGUOUS = "ambiguous", "Ambiguous"
    INVALID_INPUT = "invalid_input", "Invalid Input"


class DirectoryChangeJobStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PREVIEW_READY = "preview_ready", "Preview Ready"
    APPROVED = "approved", "Approved"
    RUNNING = "running", "Running"
    COMPLETED = "completed", "Completed"
    PARTIAL = "partial", "Partial"
    FAILED = "failed", "Failed"


class DirectoryChangeJobType(models.TextChoices):
    OU_CORRECTION = "ou_correction", "OU Correction"
    PROFILE_UPDATE = "profile_update", "Profile Update"
    BULK_OU_CORRECTION = "bulk_ou_correction", "Bulk OU Correction"


class DirectoryChangeScopeType(models.TextChoices):
    SINGLE = "single", "Single"
    BULK = "bulk", "Bulk"
    ISSUE_SELECTION = "issue_selection", "Issue Selection"


class EmailCollisionStrategy(models.TextChoices):
    APPEND_NUMERIC = "append_numeric", "Append Numeric"
    FAIL = "fail", "Fail"


class ProvisioningMode(models.TextChoices):
    SINGLE = "single", "Single"
    BULK = "bulk", "Bulk"


class ProvisioningStatus(models.TextChoices):
    PREVIEWED = "previewed", "Previewed"
    APPROVED = "approved", "Approved"
    EXECUTED = "executed", "Executed"
    FAILED = "failed", "Failed"


class ApprovalRequestStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    CANCELLED = "cancelled", "Cancelled"
    EXECUTED = "executed", "Executed"
    EXECUTION_FAILED = "execution_failed", "Execution Failed"


class ApprovalExecutionStatus(models.TextChoices):
    NOT_STARTED = "not_started", "Not Started"
    READY_TO_EXECUTE = "ready_to_execute", "Ready To Execute"
    EXECUTED = "executed", "Executed"
    EXECUTION_FAILED = "execution_failed", "Execution Failed"


class ApprovalActionType(models.TextChoices):
    BULK_CHANGE_JOB_EXECUTE = "bulk_change_job_execute", "Bulk Change Job Execute"
    BULK_PROVISIONING_CREATE = "bulk_provisioning_create", "Bulk Provisioning Create"
    HIGH_RISK_MUTATION = "high_risk_mutation", "High Risk Mutation"


class ApprovalTargetType(models.TextChoices):
    CHANGE_JOB = "change_job", "Change Job"
    PROVISIONING_BATCH = "provisioning_batch", "Provisioning Batch"
    MUTATION_SCOPE = "mutation_scope", "Mutation Scope"


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255, blank=True)
    google_id = models.CharField(max_length=255, blank=True)
    google_scopes = models.TextField(blank=True)
    google_scopes_json = models.JSONField(default=list, blank=True)
    access_token = models.TextField(blank=True)
    refresh_token_encrypted = models.TextField(blank=True)
    token_meta_json = models.JSONField(default=dict, blank=True)
    google_last_refresh_at = models.DateTimeField(null=True, blank=True)
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.OPERATOR)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def _fernet(self):
        key = settings.TOKEN_ENCRYPTION_KEY
        if not key:
            raise ImproperlyConfigured("TOKEN_ENCRYPTION_KEY is required")
        return Fernet(key.encode())

    def set_refresh_token(self, token: str):
        if not token:
            self.refresh_token_encrypted = ""
            return
        self.refresh_token_encrypted = self._fernet().encrypt(token.encode()).decode()

    def get_refresh_token(self):
        if not self.refresh_token_encrypted:
            return ""
        try:
            return self._fernet().decrypt(self.refresh_token_encrypted.encode()).decode()
        except InvalidToken:
            return ""

    @property
    def is_admin_role(self) -> bool:
        return bool(self.is_staff or self.is_superuser or self.role == UserRole.ADMIN)

    @property
    def is_operator_role(self) -> bool:
        return bool(self.is_admin_role or self.role == UserRole.OPERATOR)


class Course(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="courses")
    google_course_id = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    section = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ("user", "google_course_id")


class Session(models.Model):
    STATUS_PENDING = "pending"
    STATUS_SCHEDULED = "scheduled"
    STATUS_POSTED = "posted"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_SCHEDULED, "Scheduled"),
        (STATUS_POSTED, "Posted"),
        (STATUS_FAILED, "Failed"),
    ]

    POST_TYPE_MATERIAL = "material"
    POST_TYPE_ANNOUNCEMENT = "announcement"
    POST_TYPE_CHOICES = [
        (POST_TYPE_MATERIAL, "Material"),
        (POST_TYPE_ANNOUNCEMENT, "Announcement"),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="sessions")
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    title = models.CharField(max_length=255)
    topic = models.CharField(max_length=255, blank=True)
    subject = models.CharField(max_length=255, blank=True)
    group = models.CharField(max_length=255, blank=True)
    meet_required = models.BooleanField(default=True)
    post_type = models.CharField(max_length=30, choices=POST_TYPE_CHOICES, default=POST_TYPE_MATERIAL)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)


class MeetEvent(models.Model):
    session = models.OneToOneField(Session, on_delete=models.CASCADE, related_name="meet_event")
    calendar_event_id = models.CharField(max_length=255)
    meet_link = models.URLField(max_length=1000)


class ClassroomPost(models.Model):
    session = models.OneToOneField(Session, on_delete=models.CASCADE, related_name="classroom_post")
    google_post_id = models.CharField(max_length=255, blank=True)
    scheduled_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Session.STATUS_CHOICES, default=Session.STATUS_PENDING)


class PostLog(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="logs")
    status = models.CharField(max_length=20, choices=Session.STATUS_CHOICES)
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class ImportBatch(models.Model):
    SOURCE_GOOGLE_SHEET = "google_sheet"
    SOURCE_CSV = "csv"
    SOURCE_CHOICES = [
        (SOURCE_GOOGLE_SHEET, "Google Sheet"),
        (SOURCE_CSV, "CSV"),
    ]

    STATUS_PENDING = "pending"
    STATUS_SUCCESS = "success"
    STATUS_PARTIAL = "partial"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_PARTIAL, "Partial"),
        (STATUS_FAILED, "Failed"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="import_batches"
    )
    source_type = models.CharField(max_length=30, choices=SOURCE_CHOICES)
    source_ref = models.TextField()
    spreadsheet_id = models.CharField(max_length=255, blank=True)
    sheet_name = models.CharField(max_length=255, blank=True)
    target_date = models.DateField(null=True, blank=True)
    row_count = models.IntegerField(default=0)
    valid_count = models.IntegerField(default=0)
    invalid_count = models.IntegerField(default=0)
    duplicate_count = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    diagnostics_json = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)


class SessionDraft(models.Model):
    PUBLISH_MODE_SCHEDULED = "scheduled"
    PUBLISH_MODE_NOW = "now"
    PUBLISH_MODE_CHOICES = [
        (PUBLISH_MODE_SCHEDULED, "Scheduled"),
        (PUBLISH_MODE_NOW, "Publish Now"),
    ]

    STATUS_PENDING = "pending"
    STATUS_ACCEPTED = "accepted"
    STATUS_REJECTED = "rejected"
    STATUS_DUPLICATE = "duplicate"
    STATUS_PROMOTED = "promoted"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_DUPLICATE, "Duplicate"),
        (STATUS_PROMOTED, "Promoted to Session"),
    ]

    import_batch = models.ForeignKey(
        ImportBatch, on_delete=models.CASCADE, related_name="session_drafts"
    )
    course = models.ForeignKey(
        Course, on_delete=models.SET_NULL, null=True, blank=True, related_name="session_drafts"
    )
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    title = models.CharField(max_length=255)
    subject = models.CharField(max_length=255, blank=True)
    topic = models.CharField(max_length=255, blank=True)
    subgroup_label = models.CharField(max_length=255, blank=True)
    requires_meet = models.BooleanField(default=True)
    publish_mode = models.CharField(
        max_length=30, choices=PUBLISH_MODE_CHOICES, default=PUBLISH_MODE_SCHEDULED
    )
    scheduled_for = models.DateTimeField(null=True, blank=True)
    topic_label = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    dedupe_hash = models.CharField(max_length=64, blank=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACCEPTED)
    validation_errors_json = models.JSONField(default=list)
    row_index = models.IntegerField(default=0)
    promoted_session = models.OneToOneField(
        Session, on_delete=models.SET_NULL, null=True, blank=True, related_name="source_draft"
    )
    created_at = models.DateTimeField(auto_now_add=True)


# ---------------------------------------------------------------------------
# Phase 2 — Admin Commands + Enrollment Models
# ---------------------------------------------------------------------------


class DirectoryTarget(models.Model):
    """Cached reference to a Google Group, user, or Classroom course."""
    target_type = models.CharField(max_length=20, choices=TargetType.choices)
    external_id = models.CharField(max_length=255, db_index=True)
    email = models.EmailField(blank=True, db_index=True)
    display_name = models.CharField(max_length=255, blank=True)
    metadata_json = models.JSONField(default=dict)
    synced_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("target_type", "external_id")

    def __str__(self):
        return f"{self.target_type}:{self.email or self.external_id}"


class OnboardingBundle(models.Model):
    """Named bundle of group + course enrollment targets for onboarding."""
    name = models.CharField(max_length=255)
    role_type = models.CharField(max_length=20, choices=RoleType.choices, default=RoleType.STUDENT)
    groups_json = models.JSONField(default=list, help_text="List of Google Group emails")
    classroom_courses_json = models.JSONField(default=list, help_text="List of Google Classroom course IDs")
    description = models.TextField(blank=True, null=True)
    active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="onboarding_bundles"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class CommandJob(models.Model):
    """Top-level record for a batch admin command operation."""
    job_type = models.CharField(max_length=50, choices=ActionType.choices)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="command_jobs"
    )
    status = models.CharField(max_length=20, choices=JobStatus.choices, default=JobStatus.PENDING)
    dry_run = models.BooleanField(default=False)
    target_summary_json = models.JSONField(default=dict, help_text="Request payload summary")
    result_summary_json = models.JSONField(default=dict, help_text="Execution result summary")
    scheduled_for = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Job#{self.pk} {self.job_type} [{self.status}]"


class CommandJobItem(models.Model):
    """Per-target item within a CommandJob."""
    command_job = models.ForeignKey(CommandJob, on_delete=models.CASCADE, related_name="items")
    target_type = models.CharField(max_length=20, choices=TargetType.choices)
    target_ref = models.CharField(max_length=255, help_text="Email or external ID of target")
    action = models.CharField(max_length=50, choices=ActionType.choices)
    payload_json = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=ItemStatus.choices, default=ItemStatus.PENDING)
    result_json = models.JSONField(default=dict)
    retry_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Item#{self.pk} {self.action} {self.target_ref} [{self.status}]"


# ---------------------------------------------------------------------------
# Module B — Directory Operations Models
# ---------------------------------------------------------------------------


class DirectoryUser(models.Model):
    google_user_id = models.CharField(max_length=255, unique=True, db_index=True)
    primary_email = models.EmailField(unique=True, db_index=True)
    full_name = models.CharField(max_length=255, blank=True)
    given_name = models.CharField(max_length=255, blank=True)
    family_name = models.CharField(max_length=255, blank=True)
    org_unit_path = models.CharField(max_length=255, blank=True)
    user_category = models.CharField(
        max_length=20, choices=DirectoryUserCategory.choices, default=DirectoryUserCategory.OTHER
    )
    external_identifier = models.CharField(max_length=100, blank=True, db_index=True)
    roll_number = models.CharField(max_length=100, blank=True, db_index=True)
    employee_id = models.CharField(max_length=100, blank=True, db_index=True)
    department = models.CharField(max_length=100, blank=True)
    program = models.CharField(max_length=100, blank=True)
    batch = models.CharField(max_length=100, blank=True)
    year = models.CharField(max_length=50, blank=True)
    suspended = models.BooleanField(default=False)
    archived = models.BooleanField(default=False)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    sync_source = models.CharField(max_length=50, default="google_directory")
    expected_org_unit_path = models.CharField(max_length=255, blank=True)
    expected_email_valid = models.BooleanField(null=True, blank=True)
    aliases_json = models.JSONField(default=list)
    phones_json = models.JSONField(default=list)
    normalized_email = models.CharField(max_length=255, blank=True, db_index=True)
    normalized_full_name = models.CharField(max_length=255, blank=True, db_index=True)
    normalized_phone = models.CharField(max_length=64, blank=True, db_index=True)
    is_active = models.BooleanField(default=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    metadata_json = models.JSONField(default=dict)
    raw_payload_json = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["primary_email"]

    def __str__(self):
        return self.primary_email


class DirectorySyncJob(models.Model):
    started_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="directory_sync_jobs"
    )
    status = models.CharField(
        max_length=20, choices=DirectorySyncJobStatus.choices, default=DirectorySyncJobStatus.QUEUED
    )
    query = models.CharField(max_length=255, blank=True)
    max_results = models.IntegerField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    pages_fetched = models.IntegerField(default=0)
    users_fetched_total = models.IntegerField(default=0)
    users_upserted_total = models.IntegerField(default=0)
    users_created_total = models.IntegerField(default=0)
    users_updated_total = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)
    result_summary_json = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"DirectorySyncJob#{self.pk} [{self.status}]"


class DirectoryVerifyJob(models.Model):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="directory_verify_jobs"
    )
    source_filename = models.CharField(max_length=255)
    source_type = models.CharField(max_length=20)
    status = models.CharField(
        max_length=20, choices=DirectoryVerifyJobStatus.choices, default=DirectoryVerifyJobStatus.UPLOADED
    )
    row_count = models.IntegerField(default=0)
    summary_json = models.JSONField(default=dict)
    column_mapping_json = models.JSONField(default=dict)
    sheet_name = models.CharField(max_length=255, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"DirectoryVerifyJob#{self.pk} [{self.status}]"


class DirectoryVerifyRow(models.Model):
    job = models.ForeignKey(DirectoryVerifyJob, on_delete=models.CASCADE, related_name="rows")
    row_no = models.IntegerField()
    input_json = models.JSONField(default=dict)
    matched_directory_user = models.ForeignKey(
        DirectoryUser, on_delete=models.SET_NULL, null=True, blank=True, related_name="verify_rows"
    )
    matched_email = models.CharField(max_length=255, blank=True)
    matched_name = models.CharField(max_length=255, blank=True)
    match_basis = models.CharField(max_length=50, blank=True)
    verdict = models.CharField(max_length=30, choices=DirectoryVerifyVerdict.choices)
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["row_no", "id"]

    def __str__(self):
        return f"VerifyRow#{self.pk} job={self.job_id} verdict={self.verdict}"


class OrgUnitTemplate(models.Model):
    name = models.CharField(max_length=255)
    user_category = models.CharField(
        max_length=20, choices=DirectoryUserCategory.choices, default=DirectoryUserCategory.OTHER
    )
    department = models.CharField(max_length=100, blank=True)
    program = models.CharField(max_length=100, blank=True)
    batch = models.CharField(max_length=100, blank=True)
    year = models.CharField(max_length=50, blank=True)
    target_org_unit_path = models.CharField(max_length=255)
    priority = models.PositiveIntegerField(default=100)
    rule_config_json = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["priority", "id"]

    def __str__(self):
        return self.name


class EmailTemplateRule(models.Model):
    name = models.CharField(max_length=255)
    user_category = models.CharField(
        max_length=20, choices=DirectoryUserCategory.choices, default=DirectoryUserCategory.OTHER
    )
    department = models.CharField(max_length=100, blank=True)
    program = models.CharField(max_length=100, blank=True)
    batch = models.CharField(max_length=100, blank=True)
    year = models.CharField(max_length=50, blank=True)
    email_pattern = models.CharField(
        max_length=255,
        help_text="Use placeholders: {given_name}, {family_name}, {full_name}, {identifier}",
    )
    domain = models.CharField(max_length=255)
    collision_strategy = models.CharField(
        max_length=30, choices=EmailCollisionStrategy.choices, default=EmailCollisionStrategy.APPEND_NUMERIC
    )
    normalization_rules = models.JSONField(default=dict)
    priority = models.PositiveIntegerField(default=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["priority", "id"]

    def __str__(self):
        return self.name


class DirectoryIssue(models.Model):
    directory_user = models.ForeignKey(
        DirectoryUser, on_delete=models.SET_NULL, null=True, blank=True, related_name="issues"
    )
    issue_type = models.CharField(max_length=64, choices=DirectoryIssueType.choices)
    severity = models.CharField(max_length=20, choices=IssueSeverity.choices, default=IssueSeverity.WARNING)
    actual_value = models.TextField(blank=True)
    expected_value = models.TextField(blank=True)
    suggested_action = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=30, choices=DirectoryIssueStatus.choices, default=DirectoryIssueStatus.DETECTED
    )
    detected_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_issues"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True)
    metadata_json = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-detected_at"]

    def __str__(self):
        return f"{self.issue_type}:{self.directory_user_id or 'unknown'}"


class DirectoryChangeJob(models.Model):
    job_type = models.CharField(max_length=50, choices=DirectoryChangeJobType.choices)
    scope_type = models.CharField(max_length=30, choices=DirectoryChangeScopeType.choices)
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="directory_change_jobs"
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_directory_change_jobs",
    )
    preview_of = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="execution_jobs"
    )
    is_dry_run = models.BooleanField(default=True)
    requires_admin_approval = models.BooleanField(default=False)
    input_payload = models.JSONField(default=dict)
    preview_summary = models.JSONField(default=dict)
    execution_summary = models.JSONField(default=dict)
    status = models.CharField(
        max_length=30, choices=DirectoryChangeJobStatus.choices, default=DirectoryChangeJobStatus.PENDING
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"DirectoryJob#{self.pk} {self.job_type} [{self.status}]"


class DirectoryChangeJobItem(models.Model):
    job = models.ForeignKey(DirectoryChangeJob, on_delete=models.CASCADE, related_name="items")
    directory_user = models.ForeignKey(
        DirectoryUser, on_delete=models.SET_NULL, null=True, blank=True, related_name="change_items"
    )
    issue = models.ForeignKey(
        DirectoryIssue, on_delete=models.SET_NULL, null=True, blank=True, related_name="change_items"
    )
    target_ref = models.CharField(max_length=255)
    action = models.CharField(max_length=64)
    before_value = models.TextField(blank=True)
    after_value = models.TextField(blank=True)
    payload_json = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=ItemStatus.choices, default=ItemStatus.PENDING)
    result_json = models.JSONField(default=dict)
    error_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"DirectoryItem#{self.pk} {self.action} [{self.status}]"


class ProvisioningRecord(models.Model):
    full_name = models.CharField(max_length=255)
    given_name = models.CharField(max_length=255, blank=True)
    family_name = models.CharField(max_length=255, blank=True)
    user_category = models.CharField(
        max_length=20, choices=DirectoryUserCategory.choices, default=DirectoryUserCategory.OTHER
    )
    source_identifier = models.CharField(max_length=100, blank=True)
    generated_email = models.EmailField(blank=True, db_index=True)
    target_org_unit_path = models.CharField(max_length=255, blank=True)
    temp_password_policy = models.CharField(max_length=100, default="change_on_first_login")
    provisioning_mode = models.CharField(max_length=20, choices=ProvisioningMode.choices, default=ProvisioningMode.SINGLE)
    status = models.CharField(max_length=20, choices=ProvisioningStatus.choices, default=ProvisioningStatus.PREVIEWED)
    google_user_id = models.CharField(max_length=255, blank=True)
    preview_payload = models.JSONField(default=dict)
    execution_payload = models.JSONField(default=dict)
    failure_reason = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="provisioning_records"
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_provisioning_records",
    )
    change_job = models.ForeignKey(
        DirectoryChangeJob, on_delete=models.SET_NULL, null=True, blank=True, related_name="provisioning_records"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.generated_email or self.full_name


class ApprovalRequest(models.Model):
    action_type = models.CharField(max_length=100, choices=ApprovalActionType.choices)
    target_type = models.CharField(max_length=50, choices=ApprovalTargetType.choices)
    target_reference = models.CharField(max_length=255, db_index=True)
    payload = models.JSONField(default=dict)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="approval_requests"
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=30, choices=ApprovalRequestStatus.choices, default=ApprovalRequestStatus.PENDING)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_approval_requests",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)
    linked_change_job = models.ForeignKey(
        DirectoryChangeJob, on_delete=models.SET_NULL, null=True, blank=True, related_name="approval_requests"
    )
    linked_provisioning_record = models.ForeignKey(
        ProvisioningRecord, on_delete=models.SET_NULL, null=True, blank=True, related_name="approval_requests"
    )
    execution_status = models.CharField(
        max_length=30, choices=ApprovalExecutionStatus.choices, default=ApprovalExecutionStatus.NOT_STARTED
    )
    execution_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"ApprovalRequest#{self.pk} {self.action_type} [{self.status}]"


class DirectoryAuditLog(models.Model):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="directory_audit_logs"
    )
    action_type = models.CharField(max_length=100)
    target_type = models.CharField(max_length=50, blank=True)
    target_ref = models.CharField(max_length=255, blank=True, db_index=True)
    is_dry_run = models.BooleanField(default=False)
    success = models.BooleanField(default=False)
    before_json = models.JSONField(default=dict)
    after_json = models.JSONField(default=dict)
    request_json = models.JSONField(default=dict)
    response_json = models.JSONField(default=dict)
    error_message = models.TextField(blank=True)
    external_reference = models.CharField(max_length=255, blank=True)
    correlation_id = models.CharField(max_length=255, blank=True, db_index=True)
    approval_request = models.ForeignKey(
        ApprovalRequest, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs"
    )
    linked_change_job = models.ForeignKey(
        DirectoryChangeJob, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs"
    )
    linked_provisioning_record = models.ForeignKey(
        ProvisioningRecord, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action_type}:{self.target_ref}"

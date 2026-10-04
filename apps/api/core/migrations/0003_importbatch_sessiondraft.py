import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_user_google_scopes"),
    ]

    operations = [
        migrations.CreateModel(
            name="ImportBatch",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "source_type",
                    models.CharField(
                        choices=[("google_sheet", "Google Sheet"), ("csv", "CSV")],
                        max_length=30,
                    ),
                ),
                ("source_ref", models.TextField()),
                ("spreadsheet_id", models.CharField(blank=True, max_length=255)),
                ("sheet_name", models.CharField(blank=True, max_length=255)),
                ("target_date", models.DateField(blank=True, null=True)),
                ("row_count", models.IntegerField(default=0)),
                ("valid_count", models.IntegerField(default=0)),
                ("invalid_count", models.IntegerField(default=0)),
                ("duplicate_count", models.IntegerField(default=0)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("success", "Success"),
                            ("partial", "Partial"),
                            ("failed", "Failed"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("diagnostics_json", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="import_batches",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="SessionDraft",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("date", models.DateField()),
                ("start_time", models.TimeField()),
                ("end_time", models.TimeField()),
                ("title", models.CharField(max_length=255)),
                ("subject", models.CharField(blank=True, max_length=255)),
                ("topic", models.CharField(blank=True, max_length=255)),
                ("subgroup_label", models.CharField(blank=True, max_length=255)),
                ("requires_meet", models.BooleanField(default=True)),
                (
                    "publish_mode",
                    models.CharField(
                        choices=[("scheduled", "Scheduled"), ("now", "Publish Now")],
                        default="scheduled",
                        max_length=30,
                    ),
                ),
                ("scheduled_for", models.DateTimeField(blank=True, null=True)),
                ("topic_label", models.CharField(blank=True, max_length=255)),
                ("notes", models.TextField(blank=True)),
                (
                    "dedupe_hash",
                    models.CharField(blank=True, db_index=True, max_length=64),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("accepted", "Accepted"),
                            ("rejected", "Rejected"),
                            ("duplicate", "Duplicate"),
                            ("promoted", "Promoted to Session"),
                        ],
                        default="accepted",
                        max_length=20,
                    ),
                ),
                ("validation_errors_json", models.JSONField(default=list)),
                ("row_index", models.IntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "course",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="session_drafts",
                        to="core.course",
                    ),
                ),
                (
                    "import_batch",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="session_drafts",
                        to="core.importbatch",
                    ),
                ),
                (
                    "promoted_session",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="source_draft",
                        to="core.session",
                    ),
                ),
            ],
        ),
    ]

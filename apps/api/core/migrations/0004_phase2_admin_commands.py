"""Phase 2 — Admin Commands + Enrollment data models."""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_importbatch_sessiondraft"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DirectoryTarget",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("target_type", models.CharField(
                    choices=[("group", "Google Group"), ("user", "User"), ("course", "Classroom Course")],
                    max_length=20,
                )),
                ("external_id", models.CharField(db_index=True, max_length=255)),
                ("email", models.EmailField(blank=True, db_index=True)),
                ("display_name", models.CharField(blank=True, max_length=255)),
                ("metadata_json", models.JSONField(default=dict)),
                ("synced_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"unique_together": {("target_type", "external_id")}},
        ),
        migrations.CreateModel(
            name="OnboardingBundle",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("role_type", models.CharField(
                    choices=[("student", "Student"), ("teacher", "Teacher"), ("member", "Member")],
                    default="student",
                    max_length=20,
                )),
                ("groups_json", models.JSONField(default=list, help_text="List of Google Group emails")),
                ("classroom_courses_json", models.JSONField(
                    default=list, help_text="List of Google Classroom course IDs"
                )),
                ("description", models.TextField(blank=True, null=True)),
                ("active", models.BooleanField(default=True)),
                ("created_by", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="onboarding_bundles",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="CommandJob",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("job_type", models.CharField(
                    choices=[
                        ("ADD_USER_TO_GROUP", "Add User to Group"),
                        ("REMOVE_USER_FROM_GROUP", "Remove User from Group"),
                        ("ADD_STUDENT_TO_COURSE", "Add Student to Course"),
                        ("ADD_TEACHER_TO_COURSE", "Add Teacher to Course"),
                        ("ENROLL_GROUP_TO_COURSE", "Enroll Group to Course"),
                        ("APPLY_ONBOARDING_BUNDLE", "Apply Onboarding Bundle"),
                        ("BULK_CSV_ONBOARDING", "Bulk CSV Onboarding"),
                    ],
                    max_length=50,
                )),
                ("status", models.CharField(
                    choices=[
                        ("pending", "Pending"),
                        ("running", "Running"),
                        ("completed", "Completed"),
                        ("partial", "Partial"),
                        ("failed", "Failed"),
                        ("dry_run", "Dry Run"),
                    ],
                    default="pending",
                    max_length=20,
                )),
                ("dry_run", models.BooleanField(default=False)),
                ("target_summary_json", models.JSONField(default=dict)),
                ("result_summary_json", models.JSONField(default=dict)),
                ("scheduled_for", models.DateTimeField(blank=True, null=True)),
                ("created_by", models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="command_jobs",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="CommandJobItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("command_job", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="items",
                    to="core.commandjob",
                )),
                ("target_type", models.CharField(
                    choices=[("group", "Google Group"), ("user", "User"), ("course", "Classroom Course")],
                    max_length=20,
                )),
                ("target_ref", models.CharField(max_length=255)),
                ("action", models.CharField(
                    choices=[
                        ("ADD_USER_TO_GROUP", "Add User to Group"),
                        ("REMOVE_USER_FROM_GROUP", "Remove User from Group"),
                        ("ADD_STUDENT_TO_COURSE", "Add Student to Course"),
                        ("ADD_TEACHER_TO_COURSE", "Add Teacher to Course"),
                        ("ENROLL_GROUP_TO_COURSE", "Enroll Group to Course"),
                        ("APPLY_ONBOARDING_BUNDLE", "Apply Onboarding Bundle"),
                        ("BULK_CSV_ONBOARDING", "Bulk CSV Onboarding"),
                    ],
                    max_length=50,
                )),
                ("payload_json", models.JSONField(default=dict)),
                ("status", models.CharField(
                    choices=[
                        ("pending", "Pending"),
                        ("success", "Success"),
                        ("skipped", "Skipped"),
                        ("failed", "Failed"),
                        ("retrying", "Retrying"),
                    ],
                    default="pending",
                    max_length=20,
                )),
                ("result_json", models.JSONField(default=dict)),
                ("retry_count", models.IntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
    ]

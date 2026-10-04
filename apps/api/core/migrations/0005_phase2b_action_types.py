"""Phase 2B — Update ActionType choices for course lifecycle and direct removal."""

from django.db import migrations, models


FULL_ACTION_CHOICES = [
    ("ADD_USER_TO_GROUP", "Add User to Group"),
    ("REMOVE_USER_FROM_GROUP", "Remove User from Group"),
    ("ADD_STUDENT_TO_COURSE", "Add Student to Course"),
    ("ADD_TEACHER_TO_COURSE", "Add Teacher to Course"),
    ("ENROLL_GROUP_TO_COURSE", "Enroll Group to Course"),
    ("APPLY_ONBOARDING_BUNDLE", "Apply Onboarding Bundle"),
    ("BULK_CSV_ONBOARDING", "Bulk CSV Onboarding"),
    ("CREATE_COURSE", "Create Course"),
    ("ARCHIVE_COURSE", "Archive Course"),
    ("DELETE_COURSE", "Delete Course"),
    ("REMOVE_STUDENT_FROM_COURSE", "Remove Student from Course"),
    ("REMOVE_TEACHER_FROM_COURSE", "Remove Teacher from Course"),
]


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0004_phase2_admin_commands"),
    ]

    operations = [
        migrations.AlterField(
            model_name="commandjob",
            name="job_type",
            field=models.CharField(choices=FULL_ACTION_CHOICES, max_length=50),
        ),
        migrations.AlterField(
            model_name="commandjobitem",
            name="action",
            field=models.CharField(choices=FULL_ACTION_CHOICES, max_length=50),
        ),
    ]

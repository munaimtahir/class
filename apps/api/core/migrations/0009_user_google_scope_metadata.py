from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0008_directorysyncjob_directoryverifyjob_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="google_last_refresh_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="google_scopes_json",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="user",
            name="token_meta_json",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]

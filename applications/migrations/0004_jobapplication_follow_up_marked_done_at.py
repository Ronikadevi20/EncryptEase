# Generated by Django 5.2 on 2025-04-16 16:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("applications", "0003_alter_jobapplication_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="jobapplication",
            name="follow_up_marked_done_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]

# Generated by Django 5.2 on 2025-04-14 15:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='jobapplication',
            name='deadline_date',
            field=models.DateField(blank=True, null=True),
        ),
    ]

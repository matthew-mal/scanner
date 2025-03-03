# Generated by Django 5.1 on 2025-03-04 16:02

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0012_alter_casestagelog_employee_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="casestagelog",
            name="employee",
        ),
        migrations.AddField(
            model_name="casestagelog",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="stage_logs",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]

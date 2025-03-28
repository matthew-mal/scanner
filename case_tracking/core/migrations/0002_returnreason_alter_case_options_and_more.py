# Generated by Django 5.1 on 2024-12-31 16:25

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ReturnReason",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "reason",
                    models.CharField(
                        choices=[
                            ("defect", "Defect"),
                            ("wrong_design", "Wrong Design"),
                            ("chip", "Chip"),
                            ("color_mismatch", "Color Mismatch"),
                        ],
                        default="defect",
                        max_length=32,
                        unique=True,
                    ),
                ),
                (
                    "custom_reason",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
            ],
        ),
        migrations.AlterModelOptions(
            name="case",
            options={
                "ordering": ["-created_at"],
                "verbose_name": "Case",
                "verbose_name_plural": "Cases",
            },
        ),
        migrations.AlterModelOptions(
            name="casestagelog",
            options={
                "ordering": ["-start_time"],
                "verbose_name": "Case Stage Log",
                "verbose_name_plural": "Case Stage Logs",
            },
        ),
        migrations.AddField(
            model_name="case",
            name="archived_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="case",
            name="is_returned",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="case",
            name="return_description",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="casestagelog",
            name="end_time",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="casestagelog",
            name="is_returned",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="case",
            name="priority",
            field=models.CharField(
                choices=[("standard", "Standard"), ("urgent", "Urgent")],
                default="standard",
                max_length=10,
            ),
        ),
        migrations.AlterField(
            model_name="case",
            name="shade",
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name="stage",
            name="name",
            field=models.CharField(db_index=True, max_length=32, unique=True),
        ),
        migrations.AddField(
            model_name="case",
            name="return_reason",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="cases",
                to="core.returnreason",
            ),
        ),
    ]

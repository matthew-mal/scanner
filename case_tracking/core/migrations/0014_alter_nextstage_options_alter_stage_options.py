# Generated by Django 5.1 on 2025-03-26 14:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0013_remove_casestagelog_employee_casestagelog_user"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="nextstage",
            options={
                "ordering": ["display_name"],
                "verbose_name": "Next Stage",
                "verbose_name_plural": "Next Stages",
            },
        ),
        migrations.AlterModelOptions(
            name="stage",
            options={
                "ordering": ["name"],
                "verbose_name": "Stage",
                "verbose_name_plural": "Stages",
            },
        ),
    ]

from __future__ import absolute_import, unicode_literals

import os

import django
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "case_tracking.settings")
django.setup()

app = Celery("tasks")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


app.conf.beat_schedule = {
    "update-case-priority-every-15-minutes": {
        "task": "core.tasks.update_case_priority",
        "schedule": crontab(minute="*/30"),  # every 30 minutes
    },
}

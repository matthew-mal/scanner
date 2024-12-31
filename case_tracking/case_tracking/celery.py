from __future__ import absolute_import, unicode_literals

import os

import django
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "case_tracking.settings")
django.setup()

app = Celery("tasks")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

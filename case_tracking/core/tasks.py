from celery import shared_task
from django.shortcuts import get_object_or_404
from django.utils.timezone import now, timedelta

from .models import Case


@shared_task
def update_case_priority_task(case_number, priority):
    """
    Update the priority of a case manually or automatically change priority after 16 hours of inactivity.
    """
    # Get the case object
    case = get_object_or_404(Case, case_number=case_number)

    # Check if the case has been idle for more than 16 hours
    if case.updated_at + timedelta(hours=16) < now() and case.priority != "urgent":
        case.priority = "urgent"
        case.save()

    # Update priority
    case.priority = priority
    case.save()

    return f"Priority of case {case_number} updated to {priority}"

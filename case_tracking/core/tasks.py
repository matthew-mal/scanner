import logging

from celery import shared_task
from django.utils.timezone import now, timedelta

from .models import Case

logger = logging.getLogger(__name__)


@shared_task
def check_and_update_case_priorities():
    """
    Check all cases and update their priority to 'urgent' if they've been idle for more than 16 hours.
    """
    # Получаем все неархивные кейсы с приоритетом "standard"
    cases = Case.objects.filter(archived=False, is_returned=False, priority="standard")

    for case in cases:
        if case.updated_at + timedelta(hours=16) < now():
            case.priority = "urgent"
            case.save()
            logger.info(
                f"Case {case.case_number} priority escalated to 'urgent' due to 16+ hours of inactivity"
            )
        else:
            logger.debug(
                f"Case {case.case_number} still within 16-hour window, no update needed"
            )

    return "Priority check completed"

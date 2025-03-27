import logging

from celery import shared_task
from constance import config
from django.core.management import call_command
from django.utils.timezone import now, timedelta

from .models import Case, CaseStageLog, Stage

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


@shared_task
def delete_outdated_case_stage_logs():
    """
    Deletes outdated logs of case stages based on the CASE_STAGE_LOG_EXPIRES_AFTER setting.
    """
    expiration_time = now() - config.CASE_STAGE_LOG_EXPIRES_AFTER
    deleted_count, _ = CaseStageLog.objects.filter(
        created_at__lte=expiration_time
    ).delete()
    logger.info(
        f"Deleted {deleted_count} case stage logs older than {config.CASE_STAGE_LOG_EXPIRES_AFTER}."
    )
    return f"Deleted {deleted_count} logs"


@shared_task
def archive_completed_cases():
    """
    Archives completed cases that were completed earlier than AUTO_ARCHIVE_CASE_TIMEOUT.
    It is assumed that a 'completed' case is a case at the last stage without next_state_intent.
    """
    archive_threshold = now() - config.AUTO_ARCHIVE_CASE_TIMEOUT

    last_stage = Stage.objects.get(name=config.LAST_STAGE_NAME)

    completed_cases = Case.objects.filter(
        current_stage=last_stage,
        archived=False,
        next_state_intent__isnull=True,
        updated_at__lt=archive_threshold,
    )

    archived_count = 0
    for case in completed_cases:
        case.archive_case()
        logger.info(
            f"Archived case {case.case_number} (completed on {case.updated_at})"
        )
        archived_count += 1

    logger.info(
        f"Archived {archived_count} completed cases older than {config.AUTO_ARCHIVE_CASE_TIMEOUT}."
    )
    return f"Archived {archived_count} cases"


@shared_task
def backup_database():
    try:
        call_command("dbbackup")
        logger.info("Database backup completed")
    except Exception as e:
        logger.warning(f"Something went wrong {e}")
    return "Database backup completed"

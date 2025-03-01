from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils.timezone import now

from .models import Case, CaseStageLog


@receiver(pre_save, sender=CaseStageLog)
def set_end_time(sender, instance, **kwargs):
    """
    Signal handler that sets the end time for the previous stage
    when transitioning to a new stage. Also sets the start time for
    the current stage.
    """
    if instance.start_time and instance.end_time is None:
        # Fetch the last stage log for the current case, ordered by start_time
        # to ensure we are working with the most recent log.
        last_log = (
            CaseStageLog.objects.filter(case=instance.case)
            .order_by("-start_time")
            .first()
        )

        # If there is a previous log and its end_time is not set,
        # we update the previous stage's end_time to the current time.
        if last_log and last_log.end_time is None:
            last_log.end_time = now()  # Set the end time for the previous stage.
            last_log.save()

        # Set the end_time for the current stage.
        # If this is the first stage, the end_time will remain None,
        # as it hasn't been completed yet.
        instance.end_time = None if not last_log else now()


@receiver(pre_save, sender=Case)
def check_current_stage(sender, instance, **kwargs):
    """
    Ensure that the case is assigned to a stage before saving.
    """
    if not instance.current_stage:
        raise ValueError("Each case must be assigned to a stage before saving.")


@receiver(post_save, sender=Case)
def log_case_stage_transition(sender, instance, created, **kwargs):
    if created:
        # Новый кейс — логируем начальную стадию
        CaseStageLog.objects.create(
            case=instance,
            stage=instance.current_stage,
            start_time=now(),
        )
    else:
        # Существующий кейс — проверяем изменение стадии
        try:
            old_case = Case.objects.get(pk=instance.pk)
            if old_case.current_stage != instance.current_stage:
                # Завершаем предыдущий лог, если он открыт
                previous_log = instance.stage_logs_case.filter(
                    stage=old_case.current_stage, end_time__isnull=True
                ).first()
                if previous_log:
                    previous_log.end_time = now()
                    previous_log.save()
                # Создаём новый лог для текущей стадии
                CaseStageLog.objects.create(
                    case=instance,
                    stage=instance.current_stage,
                    start_time=now(),
                )
        except Case.DoesNotExist:
            raise ValueError(
                "Something went wrong."
            )  # На случай, если что-то пошло не так

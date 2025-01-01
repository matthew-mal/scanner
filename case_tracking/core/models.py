from django.db import models, transaction
from django.utils.timezone import now


class Stage(models.Model):
    """
    Represents a stage in the workflow.
    """

    name = models.CharField(max_length=32, unique=True, db_index=True)
    display_name = models.CharField(max_length=64)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]
        verbose_name = "Stage"
        verbose_name_plural = "Stages"


class NextStage(models.Model):
    """
    Represents a transition between two stages.
    """

    signal = models.CharField(max_length=32)
    display_name = models.CharField(max_length=64)

    current = models.ForeignKey(
        Stage, on_delete=models.CASCADE, related_name="current_state"
    )
    next = models.ForeignKey(Stage, on_delete=models.CASCADE, related_name="next_state")

    def __str__(self):
        return f"From {self.current.name} to {self.next.name}"

    class Meta:
        ordering = ["display_name"]
        verbose_name = "Next Stage"
        verbose_name_plural = "Next Stages"


class ReturnReason(models.Model):
    """
    Represents a reason for returning a case.
    """

    REASON_CHOICES = [
        ("defect", "Defect"),
        ("wrong_design", "Wrong Design"),
        ("chip", "Chip"),
        ("color_mismatch", "Color Mismatch"),
    ]

    reason = models.CharField(
        max_length=32, choices=REASON_CHOICES, default="defect", unique=True
    )
    custom_reason = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.custom_reason or self.reason


class Case(models.Model):
    """
    Represents a case in the system.
    """

    PRIORITY_CHOICES = [
        ("standard", "Standard"),
        ("urgent", "Urgent"),
    ]

    MATERIAL_CHOICES = [
        ("zr", "Zirconium"),
        ("pmma", "PMMA"),
        ("emax", "EMAX"),
    ]

    case_number = models.CharField(
        max_length=50,
        unique=True,
    )
    priority = models.CharField(
        max_length=10, choices=PRIORITY_CHOICES, default="standard"
    )
    material = models.CharField(max_length=10, choices=MATERIAL_CHOICES)
    shade = models.CharField(max_length=50, blank=True, null=True)
    current_stage = models.ForeignKey(Stage, on_delete=models.PROTECT)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(auto_now=True)
    archived = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)
    return_reason = models.ForeignKey(
        ReturnReason,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cases",
    )
    is_returned = models.BooleanField(default=False)
    return_description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Case #{self.case_number} - {self.priority}"

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Case"
        verbose_name_plural = "Cases"

    def get_shade(self):
        shades = {
            "urgent": "red",
            "standard": "default_color",
        }
        return shades.get(self.priority, "default_color")

    def log_transition(self, new_stage, is_return=False, reason=None):
        """
        Log the transition to a new stage, with optional return flag and reason.
        """
        CaseStageLog.objects.create(
            case=self,
            stage=new_stage,
            start_time=now(),
            reason=reason,
            is_return=is_return,
        )
        self.current_stage = new_stage
        self.save()

    def transition_stage(self, new_stage, is_return=False, reason=None):
        """
        Transition to a new stage and log the transition.
        """
        self.log_transition(new_stage=new_stage, is_return=is_return, reason=reason)

    def process_return(self, reason=None, custom_reason=None, description=None):
        """
        Process the return of a case, set the return reason and description.
        """
        if self.is_returned:
            raise ValueError("This case has already been returned.")

        with transaction.atomic():
            if reason:
                self.return_reason = reason
            if custom_reason:
                self.return_reason = ReturnReason.objects.create(
                    custom_reason=custom_reason
                )
            self.is_returned = True
            self.return_description = description
            self.save()

    def archive_case(self):
        self.archived = True
        self.archived_at = now()
        self.save()


class CaseStageLog(models.Model):
    """
    Represents a log of a case's stage transitions.
    """

    case = models.ForeignKey(Case, on_delete=models.PROTECT, related_name="stage_logs")
    stage = models.ForeignKey(
        Stage, on_delete=models.PROTECT, related_name="stage_logs"
    )
    start_time = models.DateTimeField(default=now)
    end_time = models.DateTimeField(null=True, blank=True)
    reason = models.TextField(blank=True, null=True)
    is_returned = models.BooleanField(default=False)

    def __str__(self):
        return f"Log for Case {self.case.case_number} at {self.stage}"

    class Meta:
        ordering = ["-start_time"]
        verbose_name = "Case Stage Log"
        verbose_name_plural = "Case Stage Logs"

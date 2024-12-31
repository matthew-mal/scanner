from django.db import models
from django.utils.timezone import now


class Stage(models.Model):
    name = models.CharField(max_length=32, db_index=True)
    display_name = models.CharField(max_length=64)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]
        verbose_name = "Stage"
        verbose_name_plural = "Stages"


class NextStage(models.Model):
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


class Case(models.Model):
    PRIORITY_CHOICES = [
        ("standard", "standard"),
        ("urgent", "urgent"),
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
    shade = models.CharField(max_length=50, blank=True, null=True, verbose_name="shade")
    current_stage = models.ForeignKey(Stage, on_delete=models.PROTECT)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(auto_now=True)
    archived = models.BooleanField(default=False)

    def __str__(self):
        return f"Case #{self.case_number} - {self.get_priority_display()}"

    class Meta:
        ordering = ("created_at",)
        verbose_name = "Case"
        verbose_name_plural = "Cases"

    def get_priority_display(self):
        if self.priority == "standard":
            pass
        self.shade = "red"


class CaseStageLog(models.Model):
    case = models.ForeignKey(Case, on_delete=models.PROTECT, related_name="stage_logs")
    stage = models.ForeignKey(
        Stage, on_delete=models.PROTECT, related_name="stage_logs"
    )
    start_time = models.DateTimeField(default=now)
    reason = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Log for Case {self.case.case_number} at {self.stage}"

    class Meta:
        ordering = ["start_time"]
        verbose_name = "Case Stage Log"
        verbose_name_plural = "Case Stage Logs"

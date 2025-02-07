from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.db import models, transaction
from django.utils.timezone import now
from guardian.mixins import GuardianUserMixin


class Stage(models.Model):
    """
    Represents a stage in the workflow.
    """

    name = models.CharField(max_length=32, unique=True, db_index=True)
    display_name = models.CharField(max_length=64)
    note = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "State"
        verbose_name_plural = "States"

    def __str__(self):
        return f"{self.pk} {self.name} {self.display_name}"


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

    class Meta:
        ordering = ["display_name"]
        verbose_name = "Next State"
        verbose_name_plural = "Next States"

    def __str__(self):
        return f"{self.signal} {self.current} {self.next}"


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
        ("standard", "STANDARD"),
        ("urgent", "URGENT"),
    ]

    MATERIAL_CHOICES = [
        ("zr", "Zirconium"),
        ("pmma", "PMMA"),
        ("emax", "EMAX"),
    ]

    case_number = models.CharField(max_length=100, unique=True)
    priority = models.CharField(
        max_length=10, choices=PRIORITY_CHOICES, default="standard"
    )
    material = models.CharField(
        max_length=10, choices=MATERIAL_CHOICES, null=True, blank=True
    )
    shade = models.CharField(max_length=50, blank=True, null=True)
    current_stage = models.ForeignKey(Stage, on_delete=models.PROTECT)
    next_state_intent = models.ForeignKey(
        NextStage,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
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

    case = models.ForeignKey(
        Case, on_delete=models.PROTECT, related_name="stage_logs_case"
    )
    stage = models.ForeignKey(
        Stage, on_delete=models.PROTECT, related_name="stage_logs_stage"
    )
    start_time = models.DateTimeField(default=now)
    end_time = models.DateTimeField(null=True, blank=True)
    reason = models.TextField(blank=True, null=True)
    is_returned = models.BooleanField(default=False)

    class Meta:
        ordering = ["-start_time"]
        verbose_name = "Case Stage Log"
        verbose_name_plural = "Case Stage Logs"

    def __str__(self):
        return f"Log for Case {self.case.case_number} at {self.stage}"


class CustomUser(AbstractBaseUser, PermissionsMixin, GuardianUserMixin):

    USERNAME_FIELD = "email"

    EMPLOYEE = "employee"
    MANAGER = "manager"

    USER_ROLE_CHOICES = (
        (EMPLOYEE, "Employee"),
        (MANAGER, "Manager"),
    )

    first_name = models.CharField("first name", max_length=30, blank=True)
    last_name = models.CharField("last name", max_length=150, blank=True)
    email = models.EmailField("email address", blank=True, unique=True)
    is_staff = models.BooleanField(
        "Может ли заходить в админку",
        default=False,
    )
    role = models.CharField(max_length=40, choices=USER_ROLE_CHOICES, default=EMPLOYEE)

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["id"]
        unique_together = ("email",)

    def __str__(self):
        return f"{self.full_name} {self.email}"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def full_name(self):
        return self.get_full_name()

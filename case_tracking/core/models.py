from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models, transaction
from django.utils.timezone import now
from guardian.mixins import GuardianUserMixin


class CustomUserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("The given email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)

    def get_by_natural_key(self, email):
        return self.get(email=email)


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
        "Can visit admin panel",
        default=False,
    )
    role = models.CharField(max_length=40, choices=USER_ROLE_CHOICES, default=EMPLOYEE)
    barcode = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        null=True,
        blank=True,
        help_text="Unique bar code",
    )  # Переносим barcode из Employee
    is_active = models.BooleanField(default=True)  # Для деактивации пользователей

    objects = CustomUserManager()

    class Meta:
        verbose_name = "Employee"
        verbose_name_plural = "Employees"
        ordering = ["id"]
        unique_together = ("email",)

    def __str__(self):
        return f"{self.full_name} {self.email}"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def full_name(self):
        return self.get_full_name()


class Stage(models.Model):
    """
    Represents a stage in the workflow.
    """

    name = models.CharField(max_length=32, unique=True, db_index=True)
    barcode = models.CharField(max_length=50, unique=True, db_index=True, null=True)
    display_name = models.CharField(max_length=64)
    note = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Stage"
        verbose_name_plural = "Stages"

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
        verbose_name = "Next Stage"
        verbose_name_plural = "Next Stages"

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
        ("other", "Other (Specify Below)"),
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
    barcode = models.CharField(max_length=50, unique=True, db_index=True, null=True)
    last_updated_by = models.ForeignKey(
        "CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cases_updated",
    )
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
        permissions = [
            ("view_case_processing_all_cases", "Can view all cases for processing"),
            ("manage_case", "Can manage a specific case"),
            ("archive_cases", "Can archive a specific case"),
            ("return_cases", "Can return a specific case"),
        ]

    def save(self, *args, **kwargs):
        # Проверяем, существует ли объект в базе
        if self.pk is not None:  # Обновление существующего кейса
            try:
                old_case = Case.objects.get(pk=self.pk)
                if old_case.current_stage != self.current_stage:
                    # Завершаем предыдущий открытый лог, если он есть
                    previous_log = self.stage_logs_case.filter(
                        stage=old_case.current_stage, end_time__isnull=True
                    ).first()
                    if previous_log:
                        previous_log.end_time = now()
                        previous_log.save()
                    # Логируем переход на новую стадию
                    self.log_transition(new_stage=self.current_stage)
            except Case.DoesNotExist:
                pass  # Если что-то пошло не так, пропускаем
        else:  # Новый кейс
            super().save(*args, **kwargs)  # Сначала сохраняем, чтобы был pk
            self.log_transition(new_stage=self.current_stage)
            return

        super().save(*args, **kwargs)

    def transition_stage(self, new_stage, user=None, is_return=False, reason=None):
        """
        Transition to a new stage and log the transition, associating it with a user.
        """
        self.log_transition(
            new_stage=new_stage, is_return=is_return, reason=reason, user=user
        )
        self.current_stage = new_stage
        self.last_updated_by = user
        self.updated_at = now()
        self.save()

    def log_transition(self, new_stage, is_return=False, reason=None, user=None):
        """
        Log the transition to a new stage.
        """
        previous_log = self.stage_logs_case.filter(end_time__isnull=True).first()
        if previous_log:
            previous_log.end_time = now()
            previous_log.save()
        CaseStageLog.objects.create(
            case=self,
            stage=new_stage,
            user=user,
            is_returned=is_return,
        )

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
    user = models.ForeignKey(
        "CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stage_logs",
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

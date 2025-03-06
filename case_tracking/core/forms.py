from core.models import CustomUser, Stage
from django import forms
from django.contrib.auth.forms import AuthenticationForm


class CaseProcessingForm(forms.Form):
    def __init__(self, choices_case, case_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["case_id"] = forms.ChoiceField(
            widget=forms.Select,
            choices=choices_case,
            label="Case",
            required=False,
            initial=case_id,
        )


class UserLoginForm(AuthenticationForm):
    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(
            attrs={"class": "form-control", "placeholder": "Email"}
        ),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Password"}
        )
    )

    class Meta:
        model = CustomUser
        fields = ("username", "password")


class EmployeeBarcodeAssignForm(forms.Form):
    employee_id = forms.ChoiceField(label="Employee", required=True)
    barcode = forms.CharField(
        max_length=50,
        label="Barcode",
        required=True,
        widget=forms.TextInput(
            attrs={"placeholder": "Scan Barcode", "id": "id_employee_barcode"}
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["employee_id"].choices = [
            (employee.id, employee.get_full_name())
            for employee in CustomUser.objects.all().order_by("last_name", "first_name")
        ]


class StageBarcodeAssignForm(forms.Form):
    stage_id = forms.ChoiceField(label="Stage", required=True)
    barcode = forms.CharField(
        max_length=50,
        label="Barcode",
        required=True,
        widget=forms.TextInput(
            attrs={"placeholder": "Scan Barcode", "id": "id_stage_barcode"}
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["stage_id"].choices = [
            (stage.id, stage.display_name)
            for stage in Stage.objects.all().order_by("name")
        ]

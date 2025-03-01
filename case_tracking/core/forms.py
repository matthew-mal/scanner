from core.models import CustomUser
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

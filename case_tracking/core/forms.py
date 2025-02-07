from django import forms


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

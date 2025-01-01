from django import forms
from django.contrib import admin

from .models import Case, CaseStageLog, NextStage, Stage


class CaseAdminForm(forms.ModelForm):
    class Meta:
        model = Case
        fields = "__all__"

    def clean_current_stage(self):
        current_stage = self.cleaned_data.get("current_stage")
        if not current_stage:
            raise forms.ValidationError("Необходимо указать текущий этап.")
        return current_stage


@admin.register(Stage)
class StageAdmin(admin.ModelAdmin):
    list_display = ("name", "display_name")
    search_fields = ("name",)
    list_filter = ("name",)


@admin.register(NextStage)
class NextStageAdmin(admin.ModelAdmin):
    list_display = ("display_name", "current", "next")
    search_fields = ("display_name",)
    list_filter = ("display_name",)


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    form = CaseAdminForm
    list_display = (
        "case_number",
        "priority",
        "current_stage",
        "created_at",
        "archived",
    )
    list_filter = ("priority", "current_stage", "archived")
    search_fields = ("case_number", "current_stage", "archived")
    readonly_fields = ("created_at", "updated_at")


@admin.register(CaseStageLog)
class CaseStageLogAdmin(admin.ModelAdmin):
    list_display = ("case", "stage", "start_time", "reason")
    list_filter = ("stage",)
    search_fields = ("case__case_number",)

from django import forms
from django.contrib import admin
from django.contrib.admin import AdminSite
from django.contrib.auth.admin import UserAdmin
from django.urls import path

from .admin_views import CaseProcessing
from .models import Case, CaseStageLog, CustomUser, NextStage, ReturnReason, Stage


class CustomAdminSite(AdminSite):
    site_header = "Case Processing Admin"
    site_title = "Admin Portal"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "case_processing/",
                self.admin_view(CaseProcessing.as_view()),
                name="case_processing",
            ),
        ]
        return custom_urls + urls


custom_admin_site = CustomAdminSite(name="custom_admin")


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


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ("email", "first_name", "last_name", "is_staff", "role")
    search_fields = ("email", "first_name", "last_name")
    list_editable = ("is_staff", "role")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "role")}),
        (
            "Permissions",
            {"fields": ("is_staff", "is_superuser", "groups", "user_permissions")},
        ),
    )
    ordering = ("id",)
    list_filter = ("role",)


@admin.register(ReturnReason)
class ReturnReasonAdmin(admin.ModelAdmin):
    list_display = ("id", "reason", "custom_reason")

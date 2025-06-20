from django import forms
from django.contrib import admin
from django.contrib.admin import AdminSite
from django.contrib.auth.admin import Group, UserAdmin
from django.shortcuts import render
from django.urls import path
from django_celery_beat.models import (
    ClockedSchedule,
    CrontabSchedule,
    IntervalSchedule,
    PeriodicTask,
    SolarSchedule,
)

from .admin_views import CaseProcessing
from .models import Case, CaseStageLog, CustomUser, NextStage, Stage

admin.site.unregister(Group)
admin.site.unregister(PeriodicTask)
admin.site.unregister(IntervalSchedule)
admin.site.unregister(CrontabSchedule)
admin.site.unregister(SolarSchedule)
admin.site.unregister(ClockedSchedule)

admin.site.site_header = "BDL milling Admin"
admin.site.site_title = "BDL milling Admin"
admin.site.index_title = "Welcome to BDL milling Admin"


class CustomAdminSite(AdminSite):
    site_header = "BDL milling Admin"
    site_title = "BDL milling Admin"
    index_title = "Welcome to BDL milling Admin"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "case_processing/",
                self.admin_view(CaseProcessing.as_view()),
                name="",
            ),
        ]
        return custom_urls + urls

    def index(self, request, extra_context=None):
        extra_context = extra_context or {}
        context = {
            "site_header": self.site_header,
            "site_title": self.site_title,
            "index_title": self.index_title,
            **extra_context,
        }
        return render(request, "admin/custom_index.html", context)


custom_admin_site = CustomAdminSite(name="case_processing")


class CaseAdminForm(forms.ModelForm):
    class Meta:
        model = Case
        fields = "__all__"

    def clean_current_stage(self):
        current_stage = self.cleaned_data.get("current_stage")
        if not current_stage:
            raise forms.ValidationError("You must specify the current stage.")
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
        "last_updated_by",
        "current_stage",
        "created_at",
        "archived",
        "is_returned",
    )
    list_filter = ("priority", "current_stage", "archived")
    search_fields = ("case_number", "current_stage", "archived")
    readonly_fields = ("created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        user = request.user
        if change and "current_stage" in form.changed_data:
            old_stage = Case.objects.get(pk=obj.pk).current_stage
            if old_stage != obj.current_stage:
                obj.transition_stage(new_stage=obj.current_stage, user=user)
        else:
            obj.last_updated_by = user
            super().save_model(request, obj, form, change)


@admin.register(CaseStageLog)
class CaseStageLogAdmin(admin.ModelAdmin):
    list_display = ("case", "stage", "user", "start_time", "reason")
    list_filter = ("stage",)
    search_fields = ("case__case_number",)


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ("email", "first_name", "last_name", "is_staff", "role")
    search_fields = ("email", "first_name", "last_name")
    list_editable = ("is_staff", "role")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "role", "barcode")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "first_name",
                    "last_name",
                    "role",
                    "is_staff",
                ),
            },
        ),
    )
    ordering = ("id",)
    list_filter = ("role",)

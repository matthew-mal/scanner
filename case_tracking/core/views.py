from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ValidationError
from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.utils.timezone import now, timedelta
from django.views import View
from guardian.shortcuts import get_objects_for_user

from .forms import CaseProcessingForm
from .models import Case, CaseStageLog, NextStage, ReturnReason, Stage
from .tasks import update_case_priority_task


def register_case(request):
    """
    Register a new case based on barcode scan.
    Accepts case number, priority, material, and other necessary details.
    """
    if request.method == "POST":
        case_number = request.POST.get("case_number")
        priority = request.POST.get(
            "priority", "standard"
        )  # Default to 'standard' if not provided
        material = request.POST.get("material")
        shade = request.POST.get("shade", "")
        current_stage = (
            Stage.objects.first()
        )  # Set the initial stage (could be default stage)

        # Create a new case
        case = Case.objects.create(
            case_number=case_number,
            priority=priority,
            material=material,
            shade=shade,
            current_stage=current_stage,
            created_at=now(),
        )

        return JsonResponse(
            {
                "message": "Case registered successfully",
                "case_number": case.case_number,
            },
            status=201,
        )
    else:
        return JsonResponse({"message": "Invalid request method"}, status=400)


def update_case_stage(request, case_number):
    """
    Update the case stage upon scanning a new stage.
    Ensure the stage is scanned within 5 minutes of case scan and check for duplicate stage scans.
    """
    if request.method == "POST":
        case = get_object_or_404(Case, case_number=case_number)
        new_stage_id = request.POST.get("new_stage_id")
        new_stage = get_object_or_404(Stage, id=new_stage_id)

        # Check if case has already passed 5 minutes since scanning
        if case.created_at + timedelta(minutes=5) < now():
            return JsonResponse(
                {
                    "message": f"Error: Stage scan timed out for case {case_number}. Please rescan the case."
                },
                status=400,
            )

        # Check if the stage has already been scanned
        if case.current_stage == new_stage:
            return JsonResponse(
                {
                    "message": f"Error: {new_stage.name} has already been scanned for case {case_number}."
                },
                status=400,
            )

        # Log the stage transition
        case.log_transition(new_stage)
        case.current_stage = new_stage
        case.save()

        return JsonResponse(
            {"message": f"Case {case_number} moved to {new_stage.name}"}, status=200
        )

    else:
        return JsonResponse({"message": "Invalid request method"}, status=400)


def process_return(request, case_number):
    """
    Process a return of a case by scanning it again and specifying the return reason.
    """
    if request.method == "POST":
        case = get_object_or_404(Case, case_number=case_number)

        if case.is_returned:
            return JsonResponse(
                {"message": "This case has already been returned."}, status=400
            )

        reason = request.POST.get("reason")
        custom_reason = request.POST.get("custom_reason", None)

        case.process_return(reason=reason, custom_reason=custom_reason)

        return JsonResponse(
            {"message": f"Case {case_number} processed for return"}, status=200
        )
    else:
        return JsonResponse({"message": "Invalid request method"}, status=400)


def case_list(request):
    """
    Display a list of cases with filtering options for priority and stage.
    """
    priority = request.GET.get("priority", None)
    stage_id = request.GET.get("stage", None)

    cases = Case.objects.all()

    if priority:
        cases = cases.filter(priority=priority)

    if stage_id:
        cases = cases.filter(current_stage__id=stage_id)

    case_data = [
        {
            "case_number": case.case_number,
            "current_stage": case.current_stage.name,
            "priority": case.priority,
            "time_on_stage": case.updated_at - case.created_at,
        }
        for case in cases
    ]

    return JsonResponse({"cases": case_data}, safe=False)


def archived_cases(request):
    """
    Show all archived cases.
    """
    archived_cases = Case.objects.filter(archived=True)
    archived_case_data = [
        {
            "case_number": case.case_number,
            "archived_at": case.archived_at,
            "return_reason": case.return_reason.reason if case.return_reason else None,
        }
        for case in archived_cases
    ]

    return JsonResponse({"archived_cases": archived_case_data}, safe=False)


def ensure_case_has_stage(request, case_number):
    """
    Ensure that each case has a stage assigned before saving.
    """
    if request.method == "POST":
        case = get_object_or_404(Case, case_number=case_number)

        if not case.current_stage:
            raise ValidationError(
                "Each case must be assigned to a stage before saving."
            )

        return JsonResponse({"message": "Case stage is valid and saved."}, status=200)
    else:
        return JsonResponse({"message": "Invalid request method"}, status=400)


def update_case_priority(request, case_number):
    """
    Update the priority of a case and call the Celery task to update it asynchronously.
    """
    if request.method == "POST":
        priority = request.POST.get("priority")

        # Call the Celery task asynchronously
        update_case_priority_task.delay(case_number, priority)

        return JsonResponse(
            {"message": f"Priority update for case {case_number} is in progress."},
            status=200,
        )
    else:
        return JsonResponse({"message": "Invalid request method"}, status=400)


@method_decorator(staff_member_required, name="dispatch")
class CaseProcessing(View):
    def get(self, request):
        context = {}
        choices_cases = []
        cases_data = []

        case_id = request.GET.get("case_id")

        cases = Case.objects.prefetch_related(
            "current_stage",
            Prefetch(
                "casestagelog_set",
                queryset=CaseStageLog.objects.select_related(
                    "stage", "reason"
                ).order_by("-start_time"),
            ),
        ).all()

        if not request.user.has_perm("api.view_case_processing_all_cases"):
            cases = get_objects_for_user(request.user, "manage_cases", cases)

        for case in cases:
            choices_cases.append((case.pk, f"{case.case_number} ({case.priority})"))

        cases = cases.filter(pk=case_id) if case_id else cases

        if not cases.exists():
            messages.error(request, "У вас нет доступа к обработке данных кейсов.")
            return render(request, "admin/case_processing.html", context)

        for case in cases:
            next_stages = NextStage.objects.filter(
                is_visible=True, previous_stage=case.current_stage
            )
            case_text = f"Кейс #{case.case_number}: {case.priority} - Текущая стадия: {case.current_stage.name}"
            cases_data.append((case_text, next_stages, case))

        context["cases_data"] = cases_data
        context["form"] = CaseProcessingForm(choices_cases, case_id)

        return render(request, "admin/case_processing.html", context)

    def post(self, request):
        if "transition" in request.POST:
            case = Case.objects.get(pk=request.POST["case_id"])
            new_stage = Stage.objects.get(pk=request.POST["new_stage_id"])

            if request.user.has_perm("manage_cases", case):
                case.transition_stage(new_stage=new_stage, is_return=False)
            else:
                messages.error(
                    request, "У вас нет доступа к изменению стадии данного кейса."
                )

        elif "archive" in request.POST:
            case = Case.objects.get(pk=request.POST["case_id"])

            if request.user.has_perm("archive_cases", case):
                case.archive_case()
            else:
                messages.error(request, "У вас нет доступа к архивации данного кейса.")

        elif "return" in request.POST:
            case = Case.objects.get(pk=request.POST["case_id"])
            reason = (
                ReturnReason.objects.get(pk=request.POST["return_reason_id"])
                if "return_reason_id" in request.POST
                else None
            )
            description = request.POST.get("return_description")

            if request.user.has_perm("return_cases", case):
                try:
                    case.process_return(reason=reason, description=description)
                except ValueError as e:
                    messages.error(request, str(e))
            else:
                messages.error(request, "У вас нет доступа к возврату данного кейса.")

        return redirect(request.get_full_path())

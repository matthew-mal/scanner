from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.timezone import now, timedelta

from .models import Case, Stage
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
        # material = request.POST.get("material")
        # shade = request.POST.get("shade", "")
        current_stage = (
            Stage.objects.first()
        )  # Set the initial stage (could be default stage)

        # Create a new case
        case = Case.objects.create(
            case_number=case_number,
            priority=priority,
            # material=material,
            # shade=shade,
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

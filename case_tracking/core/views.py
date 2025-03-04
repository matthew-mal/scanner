import logging

from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.timezone import now, timedelta
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .forms import UserLoginForm
from .models import Case, CustomUser, NextStage, Stage
from .serializers import BarcodeScanSerializer

logger = logging.getLogger(__name__)


def login_view(request):
    if request.method == "POST":
        form = UserLoginForm(data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                if user.role == CustomUser.MANAGER:
                    return redirect("manager_dashboard")
                return redirect("employee_dashboard")
            else:
                messages.error(request, "Invalid email or password")
        else:
            messages.error(request, "Invalid form data")
    else:
        form = UserLoginForm()
    return render(request, "users/login.html", {"form": form})


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


def format_timedelta(td):
    """
    Format time
    """
    if not td:
        return "0 min."
    total_seconds = int(td.total_seconds())
    days = total_seconds // (24 * 3600)
    hours = (total_seconds % (24 * 3600)) // 3600
    minutes = (total_seconds % 3600) // 60
    if days > 0:
        return f"{days} d., {hours} h., {minutes} min."
    elif hours > 0:
        return f"{hours} h., {minutes} min."
    else:
        return f"{minutes} min."


def case_list(request):
    """
    Display a list of cases with filtering options for priority and stage.
    """
    priority = request.GET.get("priority", None)
    stage_id = request.GET.get("stage", None)

    cases = Case.objects.filter(archived=False, is_returned=False)

    if priority:
        cases = cases.filter(priority=priority)

    if stage_id:
        cases = cases.filter(current_stage__id=stage_id)

    case_data = []
    for case in cases:
        # Используем related_name="stage_logs_case" для доступа к логам
        last_stage_log = (
            case.stage_logs_case.filter(stage=case.current_stage)
            .order_by("-start_time")
            .first()
        )
        # Если end_time есть, используем его, иначе считаем до текущего времени
        time_on_stage = (
            (last_stage_log.end_time - last_stage_log.start_time)
            if last_stage_log and last_stage_log.end_time
            else (now() - last_stage_log.start_time)
            if last_stage_log
            else (now() - case.created_at)  # if no logs, created_at
        )
        case_data.append(
            {
                "case_number": case.case_number,
                "current_stage": case.current_stage.name,
                "priority": case.priority,
                "time_on_stage": format_timedelta(time_on_stage),
            }
        )

    stages = Stage.objects.all()

    context = {
        "cases": case_data,
        "stages": stages,
        "priority": priority,
        "stage_id": stage_id,
    }

    return render(request, "cases/case_list.html", context)


def archived_case(request):
    """
    Display a list of archived cases.
    """
    archived_cases = Case.objects.filter(archived=True)
    archived_case_data = [
        {
            "case_number": case.case_number,
            "current_stage": case.current_stage.name,
            "archived_at": case.archived_at,
        }
        for case in archived_cases
    ]

    context = {
        "archived_cases": archived_case_data,
    }

    return render(request, "cases/archive_case.html", context)


def returned_case(request):
    """
    Display a list of returned cases.
    """
    returned_cases = Case.objects.filter(is_returned=True, archived=False)
    returned_case_data = [
        {
            "case_number": case.case_number,
            "current_stage": case.current_stage.name,
            "return_reason": case.return_reason.reason if case.return_reason else "",
            "return_description": case.return_description or "No description",
        }
        for case in returned_cases
    ]

    context = {
        "returned_cases": returned_case_data,
    }

    return render(request, "cases/returned_case.html", context)


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


@login_required
def manager_dashboard(request):
    if request.user.role != CustomUser.MANAGER:
        messages.error(
            request, "You don't have permission to access the manager dashboard."
        )
        return redirect("employee_dashboard")
    context = {
        "user": request.user,
        "title": "Manager Dashboard",
        "can_access_admin": request.user.is_staff,  # Для стандартного админа
        "can_access_custom_admin": request.user.role
        == CustomUser.MANAGER,  # Для кастомного
    }
    return render(request, "users/manager_dashboard.html", context)


@login_required
def employee_dashboard(request):
    if request.user.role != CustomUser.EMPLOYEE:
        # Если менеджер пытается зайти на employee_dashboard, перенаправляем его на manager_dashboard
        if request.user.role == CustomUser.MANAGER:
            return redirect("manager_dashboard")
        messages.error(request, "You don't have permission to access this page.")
        return redirect("login")
    # Здесь можно добавить логику для сотрудника
    context = {
        "user": request.user,
        "title": "Employee Dashboard",
    }
    return render(request, "users/employee_dashboard.html", context)


class ScanBarcodeView(APIView):
    def post(self, request):
        serializer = BarcodeScanSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        employee_barcode = serializer.validated_data["employee_barcode"]
        case_barcode = serializer.validated_data["case_barcode"]
        stage_barcode = serializer.validated_data["stage_barcode"]

        try:
            # Находим сотрудника
            employee = CustomUser.objects.get(barcode=employee_barcode, is_active=True)
            # Находим кейс
            case = Case.objects.get(
                barcode=case_barcode, archived=False, is_returned=False
            )
            # Находим стадию
            new_stage = Stage.objects.get(barcode=stage_barcode)
        except ObjectDoesNotExist as e:
            logger.error(f"Invalid barcode: {e}")
            return Response(
                {"error": f"Invalid barcode: {e}"}, status=status.HTTP_404_NOT_FOUND
            )

        # Проверяем, возможен ли переход
        if not NextStage.objects.filter(
            current=case.current_stage, next=new_stage
        ).exists():
            logger.error(f"Invalid transition from {case.current_stage} to {new_stage}")
            return Response(
                {
                    "error": f"Cannot transition from {case.current_stage.name} to {new_stage.name}"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Проверяем права сотрудника (можно настроить через permissions)
        # Предположим, что у Employee есть связь с группами или правами через Django Guardian
        if not request.user.has_perm(
            "core.manage_cases", case
        ):  # Если используете аутентификацию
            return Response(
                {"error": "Employee has no permission to manage this case"},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            # Выполняем переход
            case.transition_stage(new_stage=new_stage, employee=employee)
            return Response(
                {
                    "message": f"Case {case.case_number} transitioned to {new_stage.name} by {employee}"
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(f"Error during transition: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

import logging

from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.timezone import now, timedelta

from .forms import EmployeeBarcodeAssignForm, StageBarcodeAssignForm, UserLoginForm
from .models import Case, CustomUser, Stage

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
    user_id = request.GET.get("user", None)

    cases = Case.objects.filter(archived=False, is_returned=False).select_related(
        "current_stage", "last_updated_by"
    )

    if priority:
        cases = cases.filter(priority=priority)
    if stage_id:
        cases = cases.filter(current_stage__id=stage_id)
    if user_id:
        cases = cases.filter(last_updated_by__id=user_id)

    case_data = []
    for case in cases:
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
            else (now() - case.created_at)
        )
        case_data.append(
            {
                "case_number": case.case_number,
                "current_stage": case.current_stage.name,
                "priority": case.priority,
                "time_on_stage": format_timedelta(time_on_stage),
                "last_updated_by": case.last_updated_by.full_name
                if case.last_updated_by
                else "N/A",  # Добавляем пользователя
            }
        )
    case_data.sort(key=lambda x: x["priority"] != "urgent")

    stages = Stage.objects.all()
    employees = CustomUser.objects.filter(is_active=True)
    context = {
        "cases": case_data,
        "stages": stages,
        "employees": employees,
        "priority": priority,
        "stage_id": stage_id,
        "user_id": user_id,
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
def assign_employee_barcode(request):
    if request.user.role != CustomUser.MANAGER:
        messages.error(request, "You don't have permission to access this page.")
        return redirect("employee_dashboard")

    form = EmployeeBarcodeAssignForm()
    if request.method == "POST":
        form = EmployeeBarcodeAssignForm(request.POST)
        if form.is_valid():
            employee_id = int(form.cleaned_data["employee_id"])
            barcode = form.cleaned_data["barcode"]
            try:
                employee = CustomUser.objects.get(id=employee_id)
                if (
                    CustomUser.objects.filter(barcode=barcode)
                    .exclude(id=employee_id)
                    .exists()
                ):
                    messages.error(
                        request, "Этот штрихкод уже привязан к другому сотруднику"
                    )
                else:
                    employee.barcode = barcode
                    employee.save()
                    messages.success(
                        request,
                        f"Штрихкод {barcode} привязан к сотруднику {employee.get_full_name()}",
                    )
                    return redirect(
                        "assign_employee_barcode"
                    )  # Обновляем страницу после успеха
            except CustomUser.DoesNotExist:
                messages.error(request, "Сотрудник не найден")

    context = {
        "form": form,
        "title": "Привязка штрихкода к сотруднику",
    }
    return render(request, "users/assign_employee_barcode.html", context)


@login_required
def assign_stage_barcode(request):
    if request.user.role != CustomUser.MANAGER:
        messages.error(request, "You don't have permission to access this page.")
        return redirect("employee_dashboard")

    form = StageBarcodeAssignForm()
    if request.method == "POST":
        form = StageBarcodeAssignForm(request.POST)
        if form.is_valid():
            stage_id = int(form.cleaned_data["stage_id"])
            barcode = form.cleaned_data["barcode"]
            try:
                stage = Stage.objects.get(id=stage_id)
                if Stage.objects.filter(barcode=barcode).exclude(id=stage_id).exists():
                    messages.error(
                        request, "Этот штрихкод уже привязан к другой стадии"
                    )
                else:
                    stage.barcode = barcode
                    stage.save()
                    messages.success(
                        request,
                        f"Штрихкод {barcode} привязан к стадии {stage.display_name}",
                    )
                    return redirect(
                        "assign_stage_barcode"
                    )  # Обновляем страницу после успеха
            except Stage.DoesNotExist:
                messages.error(request, "Стадия не найдена")

    context = {
        "form": form,
        "title": "Привязка штрихкода к стадии",
    }
    return render(request, "users/assign_stage_barcode.html", context)


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

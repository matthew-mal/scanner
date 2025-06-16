import logging

from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils.timezone import now

from .forms import EmployeeBarcodeAssignForm, StageBarcodeAssignForm, UserLoginForm
from .models import Case, CustomUser, ReturnReason, Stage

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
    search_query = request.GET.get("search", None)

    cases = Case.objects.filter(archived=False, is_returned=False).select_related(
        "current_stage", "last_updated_by"
    )

    if priority:
        cases = cases.filter(priority=priority)
    if stage_id:
        cases = cases.filter(current_stage__id=stage_id)
    if user_id:
        cases = cases.filter(last_updated_by__id=user_id)
    if search_query:
        cases = cases.filter(
            Q(case_number__icontains=search_query) | Q(barcode__icontains=search_query)
        )

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
        "search_query": search_query,
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
        "can_access_admin": request.user.is_staff,
        "can_access_custom_admin": request.user.role == CustomUser.MANAGER,
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
                        request, "This barcode is already linked to another employee."
                    )
                else:
                    employee.barcode = barcode
                    employee.save()
                    messages.success(
                        request,
                        f"Barcode {barcode} assign to {employee.get_full_name()}",
                    )
                    return redirect(
                        "assign_employee_barcode"
                    )  # Обновляем страницу после успеха
            except CustomUser.DoesNotExist:
                messages.error(request, "The employee was not found")

    context = {
        "form": form,
        "title": "Linking a barcode to an employee",
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
                        request, "This barcode is already linked to another stage."
                    )
                else:
                    stage.barcode = barcode
                    stage.save()
                    messages.success(
                        request,
                        f"Barcode {barcode} already linked to the stage {stage.display_name}",
                    )
                    return redirect(
                        "assign_stage_barcode"
                    )  # Обновляем страницу после успеха
            except Stage.DoesNotExist:
                messages.error(request, "Stage not found")

    context = {
        "form": form,
        "title": "Linking a barcode to a stage",
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


def scan_barcodes_page(request):
    return render(
        request,
        "cases/scan_barcodes.html",
        {"reason_choices": ReturnReason.REASON_CHOICES},
    )

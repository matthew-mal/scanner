import logging

from core.forms import CaseProcessingForm
from core.models import Case, NextStage, ReturnReason, Stage
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from guardian.shortcuts import get_objects_for_user

logger = logging.getLogger(__name__)


@method_decorator(staff_member_required, name="dispatch")
class CaseProcessing(View):
    def get(self, request):
        try:
            context = {}
            choices_cases = []
            cases_data = []

            case_id = request.GET.get("case_id")
            show_all = request.GET.get("show_all") == "true"

            cases = Case.objects.prefetch_related("current_stage").filter(
                archived=False, is_returned=False
            )

            if not request.user.has_perm("core.view_case_processing_all_cases"):
                cases = get_objects_for_user(request.user, "manage_cases", cases)

            for case in cases:
                choices_cases.append((case.pk, f"{case.case_number} ({case.priority})"))

            if not show_all and case_id:
                cases = cases.filter(pk=case_id)

            if not cases.exists():
                if not choices_cases:
                    context["no_active_cases"] = True
                else:
                    messages.error(request, "You have no rights to view it.")
                return render(request, "admin/case_processing.html", context)

            for case in cases:
                next_stages = NextStage.objects.filter(current=case.current_stage)
                case_text = f"Case #{case.case_number}: {case.priority} - state: {case.current_stage.name}"
                cases_data.append((case_text, next_stages, case))

            context["cases_data"] = cases_data
            context["form"] = CaseProcessingForm(choices_cases, case_id)
            context["no_active_cases"] = False
            context[
                "return_reasons"
            ] = ReturnReason.objects.all()  # Добавлено для формы возврата

            return render(request, "admin/case_processing.html", context)
        except Exception as e:
            logger.error(f"Error in CaseProcessing view: {e}")
            return render(request, "admin/error.html", {"error": str(e)})

    def post(self, request):
        try:
            if "transition" in request.POST:
                case = Case.objects.get(pk=request.POST["case_id"])
                new_stage = Stage.objects.get(pk=request.POST["transition"])

                if request.user.has_perm("core.manage_cases", case):
                    case.transition_stage(new_stage=new_stage)
                    case.refresh_from_db()
                else:
                    messages.error(request, "You have no rights to see that stage.")

            elif "archive" in request.POST:
                case = Case.objects.get(pk=request.POST["case_id"])
                if request.user.has_perm("core.archive_cases", case):
                    case.archive_case()
                    messages.success(
                        request, f"Case #{case.case_number} archived successfully"
                    )
                else:
                    messages.error(request, "You have no rights to archive a case.")

            elif "return" in request.POST:
                case = Case.objects.get(pk=request.POST["case_id"])
                reason = (
                    ReturnReason.objects.get(pk=request.POST["return_reason_id"])
                    if "return_reason_id" in request.POST
                    else None
                )
                description = request.POST.get("core.return_description")

                if request.user.has_perm("core.return_cases", case):
                    try:
                        case.process_return(reason=reason, description=description)
                        messages.success(
                            request, f"Case #{case.case_number} returned successfully"
                        )
                    except ValueError as e:
                        messages.error(request, str(e))
                else:
                    messages.error(request, "You have no rights to return cases.")

        except Exception as e:
            logger.error(f"Error in post CaseProcessing: {e}")
            messages.error(request, "An error occurred while processing the request")

        # После любой операции возвращаемся к списку без параметров case_id
        base_url = request.path
        query_string = request.GET.copy()
        if "case_id" in query_string:
            del query_string["case_id"]
        full_url = (
            f"{base_url}?{query_string.urlencode()}" if query_string else base_url
        )
        return redirect(full_url)

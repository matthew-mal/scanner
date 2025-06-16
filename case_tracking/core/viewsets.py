from constance import config
from django.db import transaction
from django.utils.timezone import now
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Case, ReturnReason, Stage
from .serializers import BarcodeScanSerializer, CaseSerializer


class CaseViewSet(viewsets.ModelViewSet):
    queryset = Case.objects.all()
    serializer_class = BarcodeScanSerializer

    @action(detail=False, methods=["post"])
    def scan_barcodes(self, request):
        """
        Обработка сканирования трех штрихкодов: сотрудник-кейс-стадия
        """
        try:
            serializer = BarcodeScanSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            employee = serializer.validated_data["employee_barcode"]
            case_barcode = serializer.validated_data["case_barcode"]
            stage = serializer.validated_data["stage_barcode"]

            with transaction.atomic():
                if isinstance(case_barcode, Case):
                    # Если case_barcode уже объект Case, используем его
                    case = case_barcode
                    current_stage = case.current_stage

                    first_stage = Stage.objects.get(
                        stage_group=config.FIRST_STAGE_GROUP
                    )

                    if stage == current_stage:
                        return Response(
                            {
                                "error": "Invalid transition",
                                "detail": "Case is already on this stage",
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    # Проверяем, является ли это возвратом
                    if current_stage is not None:  # Не новый кейс
                        if stage.stage_group != first_stage.stage_group:
                            # Возврат на любую стадию кроме первой - ошибка
                            return Response(
                                {
                                    "error": "Invalid transition",
                                    "detail": "Cannot return case to a non-initial stage",
                                },
                                status=status.HTTP_400_BAD_REQUEST,
                            )
                        elif stage.stage_group == first_stage.stage_group:
                            # Возврат на первую стадию - требуем причину
                            reason_key = request.data.get("reason", None)
                            custom_reason = request.data.get("custom_reason", None)
                            description = request.data.get("description", None)

                            if not reason_key and not custom_reason:
                                return Response(
                                    {
                                        "error": "Reason required",
                                        "detail": "Please provide a reason why the case returned to the first stage",
                                        "requires_reason": True,
                                        "reason_choices": ReturnReason.REASON_CHOICES,
                                    },
                                    status=status.HTTP_400_BAD_REQUEST,
                                )

                            # Обрабатываем причину возврата
                            if reason_key:
                                try:
                                    reason = ReturnReason.objects.get(reason=reason_key)
                                except ReturnReason.DoesNotExist:
                                    return Response(
                                        {
                                            "error": "Invalid reason",
                                            "detail": f"Reason '{reason_key}' not found",
                                        },
                                        status=status.HTTP_400_BAD_REQUEST,
                                    )
                            elif custom_reason:
                                reason = ReturnReason.objects.create(
                                    reason="other", custom_reason=custom_reason
                                )

                            # Обрабатываем возврат
                            case.process_return(reason=reason, description=description)
                            case.transition_stage(
                                new_stage=stage,
                                user=employee,
                                is_return=True,
                                reason=reason,
                            )
                            message = f"Case #{case.case_number} returned to stage {stage.display_name}"
                            status_code = status.HTTP_200_OK

                else:
                    case = Case.objects.create(
                        case_number=f"CASE-{case_barcode}",
                        barcode=case_barcode,
                        last_updated_by=employee,
                        current_stage=stage,
                        created_at=now(),
                    )
                    message = f"Created new case #{case.case_number}"
                    status_code = status.HTTP_201_CREATED

                case_serializer = CaseSerializer(case)

                return Response(
                    {
                        "message": message,
                        "case": {
                            "data": case_serializer.data,
                            "employee": employee.get_full_name(),
                        },
                    },
                    status=status_code,
                )

        except Exception as e:
            return Response(
                {"error": "Unexpected Error", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

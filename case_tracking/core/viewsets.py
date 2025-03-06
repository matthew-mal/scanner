from django.db import transaction
from django.utils.timezone import now
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Case
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
            # Валидация через сериализатор
            serializer = BarcodeScanSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # Получаем валидированные данные
            employee = serializer.validated_data["employee_barcode"]
            case_barcode = serializer.validated_data["case_barcode"]
            stage = serializer.validated_data["stage_barcode"]

            # Используем атомарную транзакцию
            with transaction.atomic():
                try:
                    if isinstance(case_barcode, Case):
                        # Если case_barcode уже объект Case, используем его
                        case = case_barcode
                        case.transition_stage(new_stage=stage, user=employee)
                        message = f"Case #{case.case_number} moving to stage {stage.display_name}"
                        status_code = status.HTTP_200_OK

                except Case.DoesNotExist:
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

    # @action(detail=False, methods=["post"])
    # def assign_employee_barcode(self, request):
    #     """Привязка существующего штрихкода к сотруднику"""
    #     serializer = EmployeeBarcodeAssignSerializer(data=request.data)
    #     serializer.is_valid(raise_exception=True)
    #
    #     employee_id = serializer.validated_data["employee_id"]
    #     barcode = serializer.validated_data["barcode"]
    #
    #     try:
    #         employee = CustomUser.objects.get(id=employee_id)
    #         employee.barcode = barcode
    #         employee.save()
    #
    #         return Response(
    #             {
    #                 "message": f"Barcode {barcode} asigned to employee {employee.get_full_name()}",
    #                 "employee_id": employee.id,
    #                 "barcode": barcode,
    #             },
    #             status=status.HTTP_200_OK,
    #         )
    #
    #     except CustomUser.DoesNotExist:
    #         return Response(
    #             {"error": "No employee with that name found"},
    #             status=status.HTTP_404_NOT_FOUND,
    #         )
    #
    # @action(detail=False, methods=["post"])
    # def assign_stage_barcode(self, request):
    #     """Привязка существующего штрихкода к стадии"""
    #     serializer = StageBarcodeAssignSerializer(data=request.data)
    #     serializer.is_valid(raise_exception=True)
    #
    #     stage_id = serializer.validated_data["stage_id"]
    #     barcode = serializer.validated_data["barcode"]
    #
    #     try:
    #         stage = Stage.objects.get(id=stage_id)
    #         stage.barcode = barcode
    #         stage.save()
    #
    #         return Response(
    #             {
    #                 "message": f"Barcode {barcode} asigned to stage {stage.display_name}",
    #                 "stage_id": stage.id,
    #                 "barcode": barcode,
    #             },
    #             status=status.HTTP_200_OK,
    #         )
    #
    #     except Stage.DoesNotExist:
    #         return Response(
    #             {"error": "No stage with that name found"},
    #             status=status.HTTP_404_NOT_FOUND,
    #         )

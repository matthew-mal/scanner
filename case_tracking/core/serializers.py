from rest_framework import serializers

from .models import Case, CustomUser, Stage


class BarcodeScanSerializer(serializers.Serializer):
    employee_barcode = serializers.CharField(
        max_length=50, required=True, allow_blank=False
    )
    case_barcode = serializers.CharField(
        max_length=50, required=True, allow_blank=False
    )
    stage_barcode = serializers.CharField(
        max_length=50, required=True, allow_blank=False
    )

    def validate_employee_barcode(self, value):
        try:
            employee = CustomUser.objects.get(barcode=value)
            if not employee.is_active:
                raise serializers.ValidationError("Сотрудник неактивен")
            return employee
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError(
                {"employee_barcode": f"Employee with barcode {value} not found."}
            )

    def validate_case_barcode(self, value):
        # Проверяем, существует ли кейс с таким штрихкодом
        try:
            case = Case.objects.get(barcode=value)
            return case  # Возвращаем существующий кейс
        except Case.DoesNotExist:
            return value  # Возвращаем значение, если кейс не существует (будет создан позже)

    def validate_stage_barcode(self, value):
        try:
            stage = Stage.objects.get(barcode=value)
            return stage
        except Stage.DoesNotExist:
            raise serializers.ValidationError(
                {"stage_barcode": f"Stage with barcode {value} not found."}
            )

    def validate(self, data):
        # Здесь можно добавить дополнительную валидацию, если нужно проверить взаимосвязь полей
        print(f"Validated data: {data}")
        return data  # Обязательно возвращаем данные


class CaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Case
        fields = [
            "case_number",
            "barcode",
            "priority",
            "material",
            "current_stage",
            "last_updated_by",
            "created_at",
        ]


class EmployeeBarcodeAssignSerializer(serializers.Serializer):
    employee_id = serializers.IntegerField(required=True)
    barcode = serializers.CharField(max_length=50, required=True)

    def validate(self, data):
        barcode = data["barcode"]
        if (
            CustomUser.objects.filter(barcode=barcode)
            .exclude(id=data["employee_id"])
            .exists()
        ):
            raise serializers.ValidationError(
                {"barcode": "This barcode is already asigned to another employee"}
            )
        return data


class StageBarcodeAssignSerializer(serializers.Serializer):
    stage_id = serializers.IntegerField(required=True)
    barcode = serializers.CharField(max_length=50, required=True)

    def validate(self, data):
        barcode = data["barcode"]
        # Проверяем, не привязан ли штрихкод к другой стадии
        if Stage.objects.filter(barcode=barcode).exclude(id=data["stage_id"]).exists():
            raise serializers.ValidationError(
                {"barcode": "This barcode is already asigned to another stage"}
            )
        return data

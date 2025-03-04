from rest_framework import serializers


class BarcodeScanSerializer(serializers.Serializer):
    employee_barcode = serializers.CharField(max_length=50)
    case_barcode = serializers.CharField(max_length=50)
    stage_barcode = serializers.CharField(max_length=50)

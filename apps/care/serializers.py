from rest_framework import serializers
from rest_framework import serializers
from .models import CareGuide, Diagnosis, ServiceRequest, Store, VisitReservation
class DiagnosisSerializer(serializers.ModelSerializer):
    class Meta:
        model = Diagnosis
        fields = "__all__"
        read_only_fields = (
            "requested_by", "status", "result", "condition_level",
            "damage_type", "damage_description", "care_suggestion",
            "damage_location", "created_at",
        )
    def validate_product(self, product):
        if product.user != self.context["request"].user:
            raise serializers.ValidationError("본인의 제품만 선택할 수 있습니다.")
        return product

class CareGuideSerializer(serializers.ModelSerializer):
    class Meta: model, fields = CareGuide, "__all__"

class StoreSerializer(serializers.ModelSerializer):
    class Meta: model, fields = Store, "__all__"

class VisitReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisitReservation
        fields = "__all__"
        read_only_fields = ("user", "reservation_code", "status", "created_at")
    def validate_product(self, product):
        if product and product.user != self.context["request"].user:
            raise serializers.ValidationError("본인의 제품만 선택할 수 있습니다.")
        return product

class ServiceRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceRequest
        fields = "__all__"
        read_only_fields = ("user", "status", "created_at")
    def validate_product(self, product):
        if product.user != self.context["request"].user:
            raise serializers.ValidationError("본인의 제품만 선택할 수 있습니다.")
        return product

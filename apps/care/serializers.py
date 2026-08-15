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

    def validate(self, attrs):
        request = self.context["request"]
        reservation = attrs.get(
            "reservation", getattr(self.instance, "reservation", None)
        )
        product = attrs.get("product", getattr(self.instance, "product", None))
        store = attrs.get("store", getattr(self.instance, "store", None))
        if reservation and reservation.user_id != request.user.id:
            raise serializers.ValidationError(
                {"reservation": "본인의 방문 예약만 연결할 수 있습니다."}
            )
        if reservation and reservation.product_id and reservation.product_id != product.id:
            raise serializers.ValidationError(
                {"reservation": "방문 예약과 AS 요청의 제품이 일치해야 합니다."}
            )
        if reservation and store and reservation.store_id != store.id:
            raise serializers.ValidationError(
                {"store": "방문 예약과 AS 요청의 매장이 일치해야 합니다."}
            )
        return attrs

from datetime import time
from urllib.parse import quote

from django.utils import timezone
from rest_framework import serializers

from .models import (
    CareGuide,
    Diagnosis,
    ServiceRequest,
    Store,
    VisitReservation,
)


class DiagnosisSerializer(serializers.ModelSerializer):
    class Meta:
        model = Diagnosis
        fields = "__all__"
        read_only_fields = (
            "requested_by",
            "status",
            "result",
            "condition_level",
            "damage_type",
            "damage_description",
            "care_suggestion",
            "damage_location",
            "created_at",
        )

    def validate_product(self, product):
        if product.user != self.context["request"].user:
            raise serializers.ValidationError(
                "본인의 제품만 선택할 수 있습니다."
            )
        return product


class CareGuideSerializer(serializers.ModelSerializer):
    class Meta:
        model = CareGuide
        fields = "__all__"


class StoreSerializer(serializers.ModelSerializer):
    distance_km = serializers.FloatField(read_only=True)
    map_search_url = serializers.SerializerMethodField()

    class Meta:
        model = Store
        fields = (
            "id",
            "name",
            "address",
            "phone",
            "sido",
            "sigungu",
            "store_type",
            "channel",
            "official_store_id",
            "latitude",
            "longitude",
            "opening_hours",
            "supports_as",
            "source_url",
            "distance_km",
            "map_search_url",
        )

    def get_map_search_url(self, store):
        keyword = quote(f"{store.name} {store.address}")
        return f"https://map.naver.com/p/search/{keyword}"


class VisitReservationSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(
        source="product.name",
        read_only=True,
    )
    store_name = serializers.CharField(
        source="store.name",
        read_only=True,
    )
    store_detail = StoreSerializer(
        source="store",
        read_only=True,
    )

    class Meta:
        model = VisitReservation
        fields = "__all__"
        read_only_fields = (
            "user",
            "reservation_code",
            "status",
            "created_at",
        )

        # DB UniqueConstraint의 기본 메시지 대신
        # validate()에서 정의한 한국어 메시지를 사용합니다.
        validators = []

    def validate_product(self, product):
        if (
            product
            and product.user != self.context["request"].user
        ):
            raise serializers.ValidationError(
                "본인의 제품만 선택할 수 있습니다."
            )

        return product

    def validate_store(self, store):
        if not store.supports_as:
            raise serializers.ValidationError(
                "AS를 지원하는 매장만 예약할 수 있습니다."
            )

        return store

    def validate_visit_at(self, visit_at):
        if visit_at <= timezone.now():
            raise serializers.ValidationError(
                "방문 일시는 현재 이후여야 합니다."
            )

        if (
            visit_at.minute not in (0, 30)
            or visit_at.second != 0
            or visit_at.microsecond != 0
        ):
            raise serializers.ValidationError(
                "예약은 30분 단위로 선택해 주세요."
            )

        return visit_at

    def validate(self, attrs):
        request = self.context["request"]
        instance = self.instance

        product = attrs.get(
            "product",
            getattr(instance, "product", None),
        )
        diagnosis = attrs.get(
            "diagnosis",
            getattr(instance, "diagnosis", None),
        )
        store = attrs.get(
            "store",
            getattr(instance, "store", None),
        )
        visit_at = attrs.get(
            "visit_at",
            getattr(instance, "visit_at", None),
        )

        if not product:
            raise serializers.ValidationError({
                "product": "예약할 제품을 선택해 주세요."
            })

        if not store:
            raise serializers.ValidationError({
                "store": "예약할 매장을 선택해 주세요."
            })

        if diagnosis:
            if diagnosis.requested_by_id != request.user.id:
                raise serializers.ValidationError({
                    "diagnosis": (
                        "본인의 진단 결과만 연결할 수 있습니다."
                    )
                })

            if diagnosis.product_id != product.id:
                raise serializers.ValidationError({
                    "diagnosis": (
                        "진단 제품과 예약 제품이 일치해야 합니다."
                    )
                })

            if diagnosis.status != Diagnosis.Status.DONE:
                raise serializers.ValidationError({
                    "diagnosis": (
                        "완료된 진단 결과만 연결할 수 있습니다."
                    )
                })

        local_visit_at = timezone.localtime(visit_at)
        visit_time = local_visit_at.time().replace(tzinfo=None)

        opening_time = time(10, 0)
        closing_time = time(18, 0)

        if not opening_time <= visit_time < closing_time:
            raise serializers.ValidationError({
                "visit_at": (
                    "예약 가능 시간은 오전 10시부터 "
                    "오후 6시까지입니다."
                )
            })

        conflicts = VisitReservation.objects.filter(
            store=store,
            visit_at=visit_at,
            status=VisitReservation.Status.RESERVED,
        )

        if instance:
            conflicts = conflicts.exclude(pk=instance.pk)

        if conflicts.exists():
            raise serializers.ValidationError({
                "visit_at": "이미 예약된 방문 시간입니다."
            })

        return attrs

class ServiceRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceRequest
        fields = "__all__"
        read_only_fields = (
            "user",
            "status",
            "created_at",
        )

    def validate_product(self, product):
        if product.user != self.context["request"].user:
            raise serializers.ValidationError(
                "본인의 제품만 선택할 수 있습니다."
            )
        return product

    def validate(self, attrs):
        request = self.context["request"]

        reservation = attrs.get(
            "reservation",
            getattr(self.instance, "reservation", None),
        )
        product = attrs.get(
            "product",
            getattr(self.instance, "product", None),
        )
        store = attrs.get(
            "store",
            getattr(self.instance, "store", None),
        )

        if reservation and reservation.user_id != request.user.id:
            raise serializers.ValidationError({
                "reservation": "본인의 방문 예약만 연결할 수 있습니다."
            })

        if (
            reservation
            and reservation.product_id
            and reservation.product_id != product.id
        ):
            raise serializers.ValidationError({
                "reservation": (
                    "방문 예약과 AS 요청의 제품이 일치해야 합니다."
                )
            })

        if (
            reservation
            and store
            and reservation.store_id != store.id
        ):
            raise serializers.ValidationError({
                "store": "방문 예약과 AS 요청의 매장이 일치해야 합니다."
            })

        return attrs
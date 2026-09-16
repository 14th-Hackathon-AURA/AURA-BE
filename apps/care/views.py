import math
import secrets
import uuid
from datetime import datetime, time, timedelta

from django.db import IntegrityError, transaction
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from .business_hours import (
    STORE_TIMEZONE,
    UnknownBusinessHours,
    reservation_slots,
)
from .diagnosis_services import (
    DiagnosisProviderError,
    analyze_diagnosis_image,
)

from .models import (
    CareGuide,
    Diagnosis,
    ServiceRequest,
    Store,
    VisitReservation,
)
from .serializers import (
    CareGuideSerializer,
    DiagnosisSerializer,
    ServiceRequestSerializer,
    StoreSerializer,
    VisitReservationSerializer,
)


def calculate_distance_km(
    start_latitude,
    start_longitude,
    end_latitude,
    end_longitude,
):
    """
    두 위도·경도 사이의 직선거리를 Haversine 공식으로 계산합니다.
    반환 단위는 km입니다.
    """
    earth_radius_km = 6371.0088

    start_latitude = math.radians(float(start_latitude))
    start_longitude = math.radians(float(start_longitude))
    end_latitude = math.radians(float(end_latitude))
    end_longitude = math.radians(float(end_longitude))

    latitude_difference = end_latitude - start_latitude
    longitude_difference = end_longitude - start_longitude

    value = (
        math.sin(latitude_difference / 2) ** 2
        + math.cos(start_latitude)
        * math.cos(end_latitude)
        * math.sin(longitude_difference / 2) ** 2
    )

    central_angle = 2 * math.atan2(
        math.sqrt(value),
        math.sqrt(1 - value),
    )

    return earth_radius_km * central_angle


class DiagnosisThrottle(UserRateThrottle):
    scope = "diagnosis"


class DiagnosisViewSet(viewsets.ModelViewSet):
    serializer_class = DiagnosisSerializer

    def get_throttles(self):
        return [DiagnosisThrottle()] if self.action in {"create", "update", "partial_update", "retry"} else []

    def get_queryset(self):
        queryset = Diagnosis.objects.filter(
            requested_by=self.request.user
        ).select_related("product").order_by("-created_at", "-pk")

        product_id = self.request.query_params.get("product")
        year = self.request.query_params.get("year")

        if product_id:
            try:
                product_id = int(product_id)
                if not 1 <= product_id <= 9223372036854775807:
                    raise ValueError
            except (TypeError, ValueError):
                raise ValidationError({"product": "올바른 제품 ID를 입력해 주세요."})
            queryset = queryset.filter(product_id=product_id)

        if year:
            try:
                if not 1 <= int(year) <= 9999:
                    raise ValueError
                queryset = queryset.filter(
                    created_at__year=int(year)
                )
            except (TypeError, ValueError):
                raise ValidationError({
                    "year": "연도는 숫자로 입력해야 합니다."
                })

        return queryset
    

    def perform_create(self, serializer):
        diagnosis = serializer.save(
            requested_by=self.request.user
        )
        self._analyze(diagnosis)

    def perform_update(self, serializer):
        current = serializer.instance
        validated_data = serializer.validated_data
        product = validated_data.get("product")
        should_reanalyze = (
            "image" in validated_data
            or "checklist" in validated_data
            or (
                product is not None
                and product.pk != current.product_id
            )
        )

        if not should_reanalyze:
            serializer.save()
            return

        diagnosis = serializer.save(
            status=Diagnosis.Status.PENDING,
            result={},
            condition_level="",
            damage_type="",
            damage_description="",
            care_suggestion="",
            damage_location={},
            analysis_revision=uuid.uuid4(),
            analysis_attempts=0,
            lease_token=None,
            lease_expires_at=None,
            completed_at=None,
        )
        self._analyze(diagnosis)

    @staticmethod
    def _analyze(diagnosis):
        if settings.DIAGNOSIS_EXECUTION == "database":
            return
        from .diagnosis_jobs import run_diagnosis
        run_diagnosis(diagnosis, analyzer=analyze_diagnosis_image)
        diagnosis.refresh_from_db()

    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        diagnosis = self.get_object()
        updated = Diagnosis.objects.filter(pk=diagnosis.pk, status=Diagnosis.Status.FAILED).update(
            status=Diagnosis.Status.PENDING, result={}, condition_level="", damage_type="",
            damage_description="", care_suggestion="", damage_location={},
            analysis_revision=uuid.uuid4(), analysis_attempts=0,
            lease_token=None, lease_expires_at=None, completed_at=None,
        )
        if not updated:
            raise ValidationError({"status": "실패한 진단만 재시도할 수 있습니다."})
        diagnosis.refresh_from_db()
        self._analyze(diagnosis)
        return Response(self.get_serializer(diagnosis).data)

    @action(detail=False, methods=["get"], url_path="filter-options")
    def filter_options(self, request):
        owned = Diagnosis.objects.filter(requested_by=request.user)
        products = list(owned.order_by("product__name").values("product_id", "product__name").distinct())
        years = [item.year for item in owned.dates("created_at", "year", order="DESC")]
        return Response({"products": products, "years": years})

class CareGuideViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CareGuideSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = CareGuide.objects.filter(
            is_published=True
        ).order_by("-created_at")

        material = self.request.query_params.get("material")
        category = self.request.query_params.get("category")
        season = self.request.query_params.get("season")
        guide_type = self.request.query_params.get("guide_type")

        if material:
            queryset = queryset.filter(material__iexact=material)

        if category:
            queryset = queryset.filter(category__iexact=category)

        if season:
            queryset = queryset.filter(season__iexact=season)

        if guide_type:
            queryset = queryset.filter(
                guide_type__iexact=guide_type
            )

        return queryset


class StoreViewSet(viewsets.ReadOnlyModelViewSet):
    """
    공식 케어 매장 조회 API입니다.

    검색:
        GET /api/stores/?q=강남

    거리순:
        GET /api/stores/?latitude=37.5172&longitude=127.0473

    검색 + 거리순:
        GET /api/stores/?q=서울&latitude=37.5172&longitude=127.0473

    가까운 2개:
        GET /api/stores/?latitude=37.5172&longitude=127.0473&limit=2
    """

    serializer_class = StoreSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Store.objects.filter(
            supports_as=True
        ).order_by("name")

        keyword = self.request.query_params.get("q", "").strip()

        if keyword:
            queryset = queryset.filter(
                Q(name__icontains=keyword)
                | Q(address__icontains=keyword)
                | Q(sido__icontains=keyword)
                | Q(sigungu__icontains=keyword)
                | Q(store_type__icontains=keyword)
                | Q(channel__icontains=keyword)
            )

        return queryset

    def _get_coordinates(self, request):
        latitude_value = request.query_params.get("latitude")
        longitude_value = request.query_params.get("longitude")

        if latitude_value is None and longitude_value is None:
            return None

        if latitude_value is None or longitude_value is None:
            raise ValidationError({
                "location": (
                    "latitude와 longitude를 함께 전달해 주세요."
                )
            })

        try:
            latitude = float(latitude_value)
            longitude = float(longitude_value)
        except (TypeError, ValueError):
            raise ValidationError({
                "location": "위도와 경도는 숫자여야 합니다."
            })

        if not -90 <= latitude <= 90:
            raise ValidationError({
                "latitude": "위도는 -90부터 90 사이여야 합니다."
            })

        if not -180 <= longitude <= 180:
            raise ValidationError({
                "longitude": "경도는 -180부터 180 사이여야 합니다."
            })

        return latitude, longitude

    def _get_limit(self, request):
        limit_value = request.query_params.get("limit")

        if not limit_value:
            return None

        try:
            limit = int(limit_value)
        except (TypeError, ValueError):
            raise ValidationError({
                "limit": "limit은 숫자여야 합니다."
            })

        if not 1 <= limit <= 100:
            raise ValidationError({
                "limit": "limit은 1부터 100 사이여야 합니다."
            })

        return limit

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        stores = list(queryset)

        coordinates = self._get_coordinates(request)
        limit = self._get_limit(request)

        if coordinates:
            current_latitude, current_longitude = coordinates

            for store in stores:
                if (
                    store.latitude is None
                    or store.longitude is None
                ):
                    store.distance_km = None
                    continue

                distance = calculate_distance_km(
                    current_latitude,
                    current_longitude,
                    store.latitude,
                    store.longitude,
                )
                store.distance_km = round(distance, 1)

            # 좌표가 있는 매장은 거리순으로 배치하고,
            # 좌표가 없는 매장은 목록 마지막에 배치합니다.
            stores.sort(
                key=lambda store: (
                    store.distance_km is None,
                    (
                        store.distance_km
                        if store.distance_km is not None
                        else float("inf")
                    ),
                    store.name,
                )
            )
        else:
            for store in stores:
                store.distance_km = None

        if limit is not None:
            stores = stores[:limit]

        serializer = self.get_serializer(stores, many=True)

        return Response({
            "count": len(stores),
            "search": request.query_params.get("q", "").strip(),
            "location_used": coordinates is not None,
            "stores": serializer.data,
        })


class VisitReservationViewSet(viewsets.ModelViewSet):
    serializer_class = VisitReservationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return VisitReservation.objects.filter(
            user=self.request.user
        ).select_related(
            "store",
            "product",
            "diagnosis",
        ).order_by("-visit_at")

    def perform_create(self, serializer):
        try:
            with transaction.atomic():
                serializer.save(
                    user=self.request.user,
                    reservation_code=self._create_reservation_code(),
                )
        except IntegrityError as exc:
            raise ValidationError({
                "visit_at": "이미 예약된 방문 시간입니다."
            }) from exc

    def _create_reservation_code(self):
        while True:
            reservation_code = secrets.token_hex(4).upper()

            if not VisitReservation.objects.filter(
                reservation_code=reservation_code
            ).exists():
                return reservation_code

    @action(
        detail=False,
        methods=["get"],
        url_path="availability",
    )
    def availability(self, request):
        store_id = request.query_params.get("store")
        date_value = request.query_params.get("date")

        if not store_id:
            raise ValidationError({
                "store": "매장을 선택해 주세요."
            })

        if not date_value:
            raise ValidationError({
                "date": "예약 날짜를 선택해 주세요."
            })

        try:
            store = Store.objects.get(
                pk=store_id,
                supports_as=True,
            )
        except (Store.DoesNotExist, ValueError) as exc:
            raise ValidationError({
                "store": "AS 예약이 가능한 매장이 아닙니다."
            }) from exc

        try:
            selected_date = datetime.strptime(
                date_value,
                "%Y-%m-%d",
            ).date()
        except ValueError as exc:
            raise ValidationError({
                "date": "날짜는 YYYY-MM-DD 형식이어야 합니다."
            }) from exc

        if selected_date < timezone.localdate(
            timezone=STORE_TIMEZONE
        ):
            raise ValidationError({
                "date": "지난 날짜는 조회할 수 없습니다."
            })

        try:
            candidate_slots = reservation_slots(
                store.opening_hours,
                selected_date,
            )
        except UnknownBusinessHours as exc:
            raise ValidationError({"store": str(exc)}) from exc

        day_start = datetime.combine(
            selected_date,
            time.min,
            tzinfo=STORE_TIMEZONE,
        )

        reserved_visit_times = set(
            VisitReservation.objects.filter(
                store=store,
                visit_at__gte=day_start,
                visit_at__lt=day_start + timedelta(days=1),
                status=VisitReservation.Status.RESERVED,
            ).values_list("visit_at", flat=True)
        )

        slots = []
        now = timezone.now()
        for current_datetime in candidate_slots:
            if current_datetime > now:
                slots.append({
                    "visit_at": current_datetime.isoformat(),
                    "time": current_datetime.strftime("%H:%M"),
                    "available": (
                        current_datetime
                        not in reserved_visit_times
                    ),
                })

        return Response({
            "store":StoreSerializer(
                store,
                context=self.get_serializer_context(),
            ).data,
            "date":date_value,
            "slots":slots,
        })


    @action(
        detail=True,
        methods=["post"],
        url_path="cancel",
    )
    def cancel(self, request, pk=None):
        reservation = self.get_object()

        if reservation.status != VisitReservation.Status.RESERVED:
            raise ValidationError({
                "status": "예약 상태인 건만 취소할 수 있습니다."
            })

        if reservation.visit_at <= timezone.now():
            raise ValidationError({
                "visit_at": (
                    "이미 방문 시간이 지난 예약은 "
                    "취소할 수 없습니다."
                )
            })

        reservation.status = VisitReservation.Status.CANCELLED
        reservation.save(update_fields=("status",))

        return Response(
            self.get_serializer(reservation).data
        )


class ServiceRequestViewSet(viewsets.ModelViewSet):
    serializer_class = ServiceRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ServiceRequest.objects.filter(
            user=self.request.user
        ).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

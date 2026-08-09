import secrets

from rest_framework import permissions, viewsets

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


class DiagnosisViewSet(viewsets.ModelViewSet):
    serializer_class = DiagnosisSerializer
    http_method_names = ("get", "post", "head", "options")

    def get_queryset(self):
        queryset = Diagnosis.objects.filter(
            requested_by=self.request.user
        ).order_by("-created_at")
        product_id = self.request.query_params.get("product")
        year = self.request.query_params.get("year")
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        if year:
            try:
                queryset = queryset.filter(created_at__year=int(year))
            except (TypeError, ValueError):
                from rest_framework.exceptions import ValidationError
                raise ValidationError({"year": "연도는 숫자로 입력해야 합니다."})
        return queryset

    def perform_create(self, serializer):
        serializer.save(requested_by=self.request.user)


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
        if material:
            queryset = queryset.filter(material__iexact=material)
        if category:
            queryset = queryset.filter(category__iexact=category)
        if season:
            queryset = queryset.filter(season__iexact=season)
        return queryset


class StoreViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = StoreSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Store.objects.all().order_by("name")


class VisitReservationViewSet(viewsets.ModelViewSet):
    serializer_class = VisitReservationSerializer

    def get_queryset(self):
        return VisitReservation.objects.filter(
            user=self.request.user
        ).order_by("-visit_at")

    def perform_create(self, serializer):
        serializer.save(
            user=self.request.user,
            reservation_code=secrets.token_hex(4).upper(),
        )


class ServiceRequestViewSet(viewsets.ModelViewSet):
    serializer_class = ServiceRequestSerializer

    def get_queryset(self):
        return ServiceRequest.objects.filter(
            user=self.request.user
        ).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

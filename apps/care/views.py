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

    def get_queryset(self):
        return Diagnosis.objects.filter(
            requested_by=self.request.user
        ).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(requested_by=self.request.user)


class CareGuideViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CareGuideSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CareGuide.objects.filter(
            is_published=True
        ).order_by("-created_at")


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
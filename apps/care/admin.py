from django.contrib import admin

from .models import (
    CareGuide,
    Diagnosis,
    ServiceRequest,
    Store,
    VisitReservation,
)


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "address",
        "phone",
        "opening_hours",
        "supports_as",
    )
    list_filter = ("supports_as",)
    search_fields = ("name", "address", "phone")


@admin.register(VisitReservation)
class VisitReservationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "reservation_code",
        "user",
        "store",
        "product",
        "visit_at",
        "status",
    )
    list_filter = ("status", "store")
    search_fields = (
        "reservation_code",
        "contact_name",
        "contact_phone",
    )
    readonly_fields = (
        "reservation_code",
        "created_at",
    )


@admin.register(Diagnosis)
class DiagnosisAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "product",
        "requested_by",
        "status",
        "condition_level",
        "created_at",
    )
    list_filter = (
        "status",
        "condition_level",
    )


@admin.register(CareGuide)
class CareGuideAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "guide_type",
        "material",
        "is_published",
    )
    list_filter = (
        "guide_type",
        "is_published",
    )


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "product",
        "store",
        "status",
        "created_at",
    )
    list_filter = ("status", "store")
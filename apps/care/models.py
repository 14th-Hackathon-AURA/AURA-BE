from django.conf import settings
from django.db import models

from apps.catalog.models import Product



class Diagnosis(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "분석 대기"
        DONE = "DONE", "분석 완료"
        FAILED = "FAILED", "분석 실패"

    class ConditionLevel(models.TextChoices):
        SAFE = "SAFE", "안전"
        CAUTION = "CAUTION", "주의"
        DANGER = "DANGER", "위험"

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="diagnoses",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    image = models.ImageField(upload_to="diagnoses/")
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    result = models.JSONField(default=dict, blank=True)
    condition_level = models.CharField(
        max_length=10,
        choices=ConditionLevel.choices,
        blank=True,
    )
    damage_type = models.CharField(max_length=80, blank=True)
    damage_description = models.TextField(blank=True)
    care_suggestion = models.TextField(blank=True)
    damage_location = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class CareGuide(models.Model):
    class GuideType(models.TextChoices):
        BASIC = "BASIC", "기본 관리"
        POST_PURCHASE = "POST_PURCHASE", "구매 직후 관리"
        AFTER_CARE = "AFTER_CARE", "사후 케어"

    title = models.CharField(max_length=120)
    guide_type = models.CharField(
        max_length=20,
        choices=GuideType.choices,
        default=GuideType.BASIC,
    )
    material = models.CharField(max_length=60)
    category = models.CharField(max_length=50, blank=True)
    content = models.TextField()
    source_name = models.CharField(max_length=120, blank=True)
    source_url = models.URLField(blank=True)
    season = models.CharField(max_length=30, blank=True)
    image = models.ImageField(
        upload_to="guides/",
        null=True,
        blank=True,
    )
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Store(models.Model):
    name = models.CharField(max_length=120)
    address = models.CharField(max_length=255)
    phone = models.CharField(max_length=30, blank=True)

    # 지역 검색용 필드
    sido = models.CharField(max_length=50, blank=True)
    sigungu = models.CharField(max_length=50, blank=True)

    # 매장 유형 및 운영 주체
    store_type = models.CharField(max_length=30, blank=True)
    channel = models.CharField(max_length=30, blank=True)

    # MCM 공식 매장 식별자
    official_store_id = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        unique=True,
    )

    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
    )
    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
    )

    opening_hours = models.CharField(max_length=150, blank=True)
    supports_as = models.BooleanField(default=True)
    source_url = models.URLField(blank=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


class VisitReservation(models.Model):
    class Status(models.TextChoices):
        RESERVED = "RESERVED", "Reserved"
        CANCELLED = "CANCELLED", "Cancelled"
        COMPLETED = "COMPLETED", "Completed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="visit_reservations",
    )
    store = models.ForeignKey(
        Store,
        on_delete=models.PROTECT,
        related_name="reservations",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    diagnosis = models.ForeignKey(
        Diagnosis,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="visit_reservations",
    )
    visit_at = models.DateTimeField()
    purpose = models.CharField(max_length=100)
    contact_name = models.CharField(max_length=50, blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    request_note = models.TextField(blank=True)
    reservation_code = models.CharField(
        max_length=16,
        unique=True,
    )
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.RESERVED,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("store", "visit_at"),
                condition=models.Q(status="RESERVED"),
                name="unique_active_store_visit_slot",
            )
        ]

    def __str__(self):
        return f"{self.reservation_code} - {self.store.name}"


class ServiceRequest(models.Model):
    class Status(models.TextChoices):
        RECEIVED = "RECEIVED", "Received"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="service_requests",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="service_requests",
    )
    store = models.ForeignKey(
        Store,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    reservation = models.OneToOneField(
        VisitReservation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    symptom = models.TextField()
    images = models.JSONField(default=list, blank=True)
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.RECEIVED,
    )
    created_at = models.DateTimeField(auto_now_add=True)
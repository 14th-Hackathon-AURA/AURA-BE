from django.conf import settings
from django.db import models
from apps.catalog.models import Product

class Diagnosis(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "분석 대기"
        DONE = "DONE", "분석 완료"
        FAILED = "FAILED", "분석 실패"
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="diagnoses")
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    image = models.ImageField(upload_to="diagnoses/")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    result = models.JSONField(default=dict, blank=True) # 손상부위·심각도·근거
    created_at = models.DateTimeField(auto_now_add=True)

class CareGuide(models.Model):
    title = models.CharField(max_length=120)
    material = models.CharField(max_length=60)
    category = models.CharField(max_length=50, blank=True)
    content = models.TextField()
    image = models.ImageField(upload_to="guides/", null=True, blank=True)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Store(models.Model):
    name = models.CharField(max_length=120)
    address = models.CharField(max_length=255)
    phone = models.CharField(max_length=30)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    opening_hours = models.CharField(max_length=150, blank=True)
    supports_as = models.BooleanField(default=True)

class VisitReservation(models.Model):
    class Status(models.TextChoices):
        RESERVED = "RESERVED", "Reserved"
        CANCELLED = "CANCELLED", "Cancelled"
        COMPLETED = "COMPLETED", "Completed"
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="visit_reservations")
    store = models.ForeignKey(Store, on_delete=models.PROTECT, related_name="reservations")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    visit_at = models.DateTimeField()
    purpose = models.CharField(max_length=100)
    request_note = models.TextField(blank=True)
    reservation_code = models.CharField(max_length=16, unique=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.RESERVED)
    created_at = models.DateTimeField(auto_now_add=True)

class ServiceRequest(models.Model):
    class Status(models.TextChoices):
        RECEIVED = "RECEIVED", "Received"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="service_requests")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    store = models.ForeignKey(Store, on_delete=models.PROTECT, null=True, blank=True)
    reservation = models.OneToOneField(VisitReservation, on_delete=models.SET_NULL, null=True, blank=True)
    symptom = models.TextField()
    images = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.RECEIVED)
    created_at = models.DateTimeField(auto_now_add=True)

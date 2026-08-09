from django.conf import settings
from django.db import models

class Profile(models.Model):
    class Gender(models.TextChoices):
        FEMALE = "FEMALE", "여성"
        MALE = "MALE", "남성"
        OTHER = "OTHER", "기타/응답 안 함"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    nickname = models.CharField(max_length=30, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    gender = models.CharField(max_length=10, choices=Gender.choices, blank=True)
    age_range = models.CharField(max_length=20, blank=True)
    preferred_categories = models.JSONField(default=list, blank=True)  # 온보딩 선호 카테고리
    lifestyle = models.JSONField(default=list, blank=True)
    preferred_brands = models.JSONField(default=list, blank=True)
    min_budget = models.PositiveIntegerField(null=True, blank=True)
    max_budget = models.PositiveIntegerField(null=True, blank=True)
    marketing_agreed = models.BooleanField(default=False)
    onboarding_completed = models.BooleanField(default=False)
    image = models.ImageField(upload_to="profiles/", null=True, blank=True)
    membership_tier = models.CharField(max_length=30, default="AURA Silver")
    membership_points = models.PositiveIntegerField(default=0)

class Notification(models.Model):
    class Type(models.TextChoices):
        CARE = "CARE", "케어 알림"
        MEMBERSHIP = "MEMBERSHIP", "멤버십"
        EVENT = "EVENT", "이벤트"
        GENERAL = "GENERAL", "일반"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    type = models.CharField(max_length=15, choices=Type.choices, default=Type.GENERAL)
    title = models.CharField(max_length=100)
    body = models.TextField()
    action_url = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

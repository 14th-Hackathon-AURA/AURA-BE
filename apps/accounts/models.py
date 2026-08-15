from django.conf import settings
from django.db import models


def calculate_membership_tier(user):
    return calculate_membership_tier_from_counts(
        user.post_set.count(), user.comment_set.count()
    )


def calculate_membership_tier_from_counts(post_count, comment_count):
    if post_count >= 200 and comment_count >= 200:
        return "AURA Diamond"
    if post_count >= 100 and comment_count >= 100:
        return "AURA Platinum"
    if post_count >= 50 and comment_count >= 50:
        return "AURA Gold"
    return "AURA Silver"

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
    event_key = models.CharField(max_length=120, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("user", "event_key"),
                condition=models.Q(event_key__isnull=False) & ~models.Q(event_key=""),
                name="unique_notification_event_per_user",
            )
        ]

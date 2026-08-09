from django.conf import settings
from django.db import models

class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    nickname = models.CharField(max_length=30, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    preferred_categories = models.JSONField(default=list, blank=True)  # 온보딩 선호 카테고리
    marketing_agreed = models.BooleanField(default=False)
    onboarding_completed = models.BooleanField(default=False)
    image = models.ImageField(upload_to="profiles/", null=True, blank=True)

class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    body = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

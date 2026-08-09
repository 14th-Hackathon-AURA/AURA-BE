from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Notification, Profile

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    class Meta:
        model = User
        fields = ("username", "email", "password")
    def create(self, data):
        user = User.objects.create_user(**data)
        Profile.objects.create(user=user)
        return user

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ("nickname", "phone", "preferred_categories", "marketing_agreed", "onboarding_completed", "image")

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ("id", "title", "body", "is_read", "created_at")
        read_only_fields = ("id", "title", "body", "created_at")

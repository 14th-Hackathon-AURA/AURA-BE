from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import Notification, Profile

class RegisterSerializer(serializers.ModelSerializer):
    username = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, min_length=8)
    class Meta:
        model = User
        fields = ("username", "email", "password")
    def create(self, data):
        if not data.get("username"):
            data["username"] = data["email"]
        user = User.objects.create_user(**data)
        Profile.objects.create(user=user)
        return user

    def validate_email(self, value):
        email = value.strip().lower()
        if not email:
            raise serializers.ValidationError("이메일은 필수입니다.")
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("이미 가입된 이메일입니다.")
        return email


class EmailOrUsernameTokenSerializer(TokenObtainPairSerializer):
    username = serializers.CharField(required=False, write_only=True)
    email = serializers.EmailField(required=False, write_only=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[self.username_field].required = False

    def validate(self, attrs):
        identifier = attrs.get("email") or attrs.get(self.username_field)
        if not identifier:
            raise serializers.ValidationError("이메일 또는 사용자 이름을 입력해주세요.")
        if identifier and "@" in identifier:
            user = User.objects.filter(email__iexact=identifier).first()
            attrs[self.username_field] = user.username if user else identifier
        return super().validate(attrs)

class ProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Profile
        fields = (
            "email", "nickname", "phone", "gender", "age_range",
            "preferred_categories", "lifestyle", "preferred_brands",
            "min_budget", "max_budget", "marketing_agreed",
            "onboarding_completed", "image", "membership_tier",
            "membership_points",
        )
        read_only_fields = ("email", "membership_tier", "membership_points")

    def validate(self, attrs):
        minimum = attrs.get("min_budget", getattr(self.instance, "min_budget", None))
        maximum = attrs.get("max_budget", getattr(self.instance, "max_budget", None))
        if minimum is not None and maximum is not None and minimum > maximum:
            raise serializers.ValidationError(
                {"max_budget": "최대 예산은 최소 예산보다 크거나 같아야 합니다."}
            )
        completing = attrs.get(
            "onboarding_completed",
            getattr(self.instance, "onboarding_completed", False),
        )
        if completing:
            required = (
                "nickname", "gender", "age_range", "preferred_categories",
                "lifestyle", "min_budget", "max_budget",
            )
            missing = [
                field for field in required
                if attrs.get(field, getattr(self.instance, field, None)) in (None, "", [])
            ]
            if missing:
                raise serializers.ValidationError(
                    {field: "온보딩 완료에 필요한 값입니다." for field in missing}
                )
        return attrs

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ("id", "type", "title", "body", "action_url", "is_read", "created_at")
        read_only_fields = ("id", "type", "title", "body", "action_url", "created_at")

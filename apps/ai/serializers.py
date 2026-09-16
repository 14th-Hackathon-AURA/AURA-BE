from rest_framework import serializers

from .catalog import get_product
from .models import ChatMessage, ChatSession, VisitCard
from .services import generate_visit_card_summary


class ChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=2000, trim_whitespace=True)
    session_id = serializers.IntegerField(required=False, min_value=1)
    product_code = serializers.CharField(
        required=False,
        allow_blank=False,
        max_length=40,
    )


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ("id", "role", "content", "metadata", "created_at")
        read_only_fields = fields


class ChatSessionSerializer(serializers.ModelSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)

    class Meta:
        model = ChatSession
        fields = (
            "id",
            "title",
            "created_at",
            "updated_at",
            "messages",
        )
        read_only_fields = ("id", "created_at", "updated_at", "messages")


class VisitCardSerializer(serializers.ModelSerializer):
    session_id = serializers.IntegerField(
        write_only=True,
        required=False,
        allow_null=True,
        min_value=1,
    )

    class Meta:
        model = VisitCard
        fields = (
            "id",
            "session_id",
            "style_code",
            "product",
            "consultation_summary",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "product",
            "consultation_summary",
            "created_at",
            "updated_at",
        )

    def validate_style_code(self, value):
        product = get_product(value)
        if not product:
            raise serializers.ValidationError("조회 가능한 MCM 상품이 아닙니다.")
        return product["style_code"]

    def validate_session_id(self, value):
        if value is None:
            return value
        request = self.context["request"]
        if not ChatSession.objects.filter(id=value, user=request.user).exists():
            raise serializers.ValidationError("본인의 상담 기록만 연결할 수 있습니다.")
        return value

    def create(self, validated_data):
        request = self.context["request"]
        style_code = validated_data["style_code"]
        product = get_product(style_code)
        session_id = validated_data.pop("session_id", None)
        card, _ = VisitCard.objects.update_or_create(
            user=request.user,
            style_code=style_code,
            defaults={
                "session_id": session_id,
                "product": product,
                "consultation_summary": generate_visit_card_summary(
                    session=(
                        ChatSession.objects.filter(id=session_id).first()
                        if session_id
                        else None
                    ),
                    user=request.user,
                    product=product,
                ),
            },
        )
        return card

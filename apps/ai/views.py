from rest_framework import permissions, status, viewsets
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.care.models import Diagnosis

from .catalog import get_product, recommend_products
from .models import ChatMessage, ChatSession, VisitCard
from .serializers import (
    ChatRequestSerializer,
    ChatSessionSerializer,
    VisitCardSerializer,
)
from .services import AIProviderError, generate_care_reply, generate_chat_reply


class AIServiceUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "AI 상담 서비스를 사용할 수 없습니다. 잠시 후 다시 시도해 주세요."


def _is_save_request(message):
    normalized = message.replace(" ", "")
    return "저장" in normalized and (
        "카드" in normalized or "추천" in normalized
    )


def _save_recommended_product(*, session, user, product_code=None):
    codes = session.last_recommendation_codes
    selected_code = product_code or (codes[0] if codes else None)
    if not selected_code or selected_code not in codes:
        return None

    product = get_product(selected_code)
    if not product:
        return None

    previous_answer = (
        session.messages.filter(role=ChatMessage.Role.ASSISTANT)
        .order_by("-created_at")
        .values_list("content", flat=True)
        .first()
        or ""
    )
    card, _ = VisitCard.objects.update_or_create(
        user=user,
        style_code=product["style_code"],
        defaults={
            "session": session,
            "product": product,
            "consultation_summary": previous_answer,
        },
    )
    return card


class ChatView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        request_serializer = ChatRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        message = request_serializer.validated_data["message"]
        session_id = request_serializer.validated_data.get("session_id")

        if session_id:
            session = ChatSession.objects.filter(
                id=session_id,
                user=request.user,
            ).first()
            if not session:
                return Response(
                    {"detail": "채팅방을 찾을 수 없습니다."},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            session = ChatSession.objects.create(
                user=request.user,
                title=message[:30],
            )

        if _is_save_request(message):
            card = _save_recommended_product(
                session=session,
                user=request.user,
                product_code=request_serializer.validated_data.get("product_code"),
            )
            if not card:
                return Response(
                    {"detail": "먼저 상품 추천을 받은 뒤 저장해 주세요."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            ChatMessage.objects.create(
                session=session,
                role=ChatMessage.Role.USER,
                content=message,
            )
            answer = f"{card.product['name']}을(를) 방문 카드로 저장했어요."
            serialized_card = VisitCardSerializer(card).data
            ChatMessage.objects.create(
                session=session,
                role=ChatMessage.Role.ASSISTANT,
                content=answer,
                metadata={"visit_card": serialized_card},
            )
            session.save(update_fields=("updated_at",))
            return Response(
                {
                    "session_id": session.id,
                    "answer": answer,
                    "recommended_products": [],
                    "visit_card": serialized_card,
                }
            )

        ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.USER,
            content=message,
        )
        profile = getattr(request.user, "profile", None)
        candidates = recommend_products(message, profile=profile, limit=3)
        try:
            answer = generate_chat_reply(
                session=session,
                user=request.user,
                candidates=candidates,
            )
        except AIProviderError as exc:
            raise AIServiceUnavailable(str(exc)) from exc

        ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.ASSISTANT,
            content=answer,
            metadata={"recommended_products": candidates},
        )
        if candidates:
            session.last_recommendation_codes = [
                item["style_code"] for item in candidates
            ]
            session.save(
                update_fields=("last_recommendation_codes", "updated_at")
            )
        else:
            session.save(update_fields=("updated_at",))

        return Response(
            {
                "session_id": session.id,
                "answer": answer,
                "recommended_products": candidates,
                "visit_card": None,
            }
        )


class ChatSessionViewSet(viewsets.ModelViewSet):
    serializer_class = ChatSessionSerializer
    http_method_names = ("get", "patch", "delete", "head", "options")

    def get_queryset(self):
        return (
            ChatSession.objects.filter(user=self.request.user)
            .prefetch_related("messages")
            .order_by("-updated_at")
        )


class VisitCardViewSet(viewsets.ModelViewSet):
    serializer_class = VisitCardSerializer
    http_method_names = ("get", "post", "delete", "head", "options")

    def get_queryset(self):
        return VisitCard.objects.filter(user=self.request.user).order_by(
            "-created_at"
        )


class CareRecommendationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        diagnosis = (
            Diagnosis.objects.filter(
                id=request.data.get("diagnosis_id"),
                requested_by=request.user,
            )
            .select_related("product")
            .first()
        )
        if not diagnosis or diagnosis.status != Diagnosis.Status.DONE:
            return Response(
                {"detail": "완료된 본인 진단 이력이 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        context = {
            "product": diagnosis.product.name,
            "brand": diagnosis.product.brand,
            "condition_level": diagnosis.condition_level,
            "damage_type": diagnosis.damage_type,
            "damage_description": diagnosis.damage_description,
            "care_suggestion": diagnosis.care_suggestion,
            "result": diagnosis.result,
        }
        try:
            recommendation = generate_care_reply(context)
        except AIProviderError as exc:
            raise AIServiceUnavailable(str(exc)) from exc
        return Response({"recommendation": recommendation})

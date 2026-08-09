import json
import os
from openai import OpenAI
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.care.models import Diagnosis
from rest_framework import viewsets
from .models import ChatMessage, ChatSession
from .serializers import ChatSessionSerializer

SYSTEM_PROMPT = """당신은 명품 가방 케어 상담사입니다. 제공된 제품 정보와 진단 결과만 근거로
안전한 관리 방법을 한국어로 제안하세요. 확실하지 않으면 전문가 AS를 권하고, 화학약품 사용은 단정하지 마세요."""

def ask_llm(message):
    # OPENAI_API_KEY가 없으면 프론트 연동용 안전한 목업 응답을 돌려준다.
    if not os.getenv("OPENAI_API_KEY"):
        return "현재는 데모 모드입니다. 사진 진단 결과를 바탕으로 전문가 상담을 권장합니다."
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    answer = client.chat.completions.create(model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"), messages=[
        {"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": message}
    ])
    return answer.choices[0].message.content

class ChatView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        message = request.data.get("message", "").strip()
        if not message: return Response({"detail": "message는 필수입니다."}, status=400)
        session_id = request.data.get("session_id")
        if session_id:
            session = ChatSession.objects.filter(id=session_id, user=request.user).first()
            if not session: return Response({"detail": "채팅방을 찾을 수 없습니다."}, status=404)
        else:
            session = ChatSession.objects.create(user=request.user, title=message[:30])
        ChatMessage.objects.create(session=session, role=ChatMessage.Role.USER, content=message)
        answer = ask_llm(message)
        ChatMessage.objects.create(session=session, role=ChatMessage.Role.ASSISTANT, content=answer)
        return Response({"session_id": session.id, "answer": answer})

class ChatSessionViewSet(viewsets.ModelViewSet):
    serializer_class = ChatSessionSerializer
    def get_queryset(self): return ChatSession.objects.filter(user=self.request.user).prefetch_related("messages").order_by("-updated_at")
    def perform_create(self, serializer): serializer.save(user=self.request.user)

class CareRecommendationView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        diagnosis = Diagnosis.objects.filter(id=request.data.get("diagnosis_id"), requested_by=request.user).first()
        if not diagnosis or diagnosis.status != Diagnosis.Status.DONE:
            return Response({"detail": "완료된 본인 진단 이력이 필요합니다."}, status=400)
        context = json.dumps({"product": diagnosis.product.name, "brand": diagnosis.product.brand, "diagnosis": diagnosis.result}, ensure_ascii=False)
        return Response({"recommendation": ask_llm(context)})

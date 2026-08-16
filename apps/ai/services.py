import json
import os

from openai import OpenAI


SYSTEM_PROMPT = """당신은 AURA의 MCM 상품 상담사입니다.
사용자의 예산, 선호 스타일, 사용 상황을 파악해 제공된 MCM 후보 상품 안에서만 안내하세요.
상품명, 카테고리, 소재, 사이즈, 색상, 가격, 이미지, 스타일, 사용 상황은 제공된 데이터만 사실로 말하세요.
후보에 없는 상품, 가격, 재고, 매장 정책, 공식 링크를 지어내지 마세요.
추천할 때는 최대 3개만 제시하고 각 상품이 조건에 맞는 이유를 짧게 설명하세요.
필요한 조건이 부족하면 예산, 스타일, 사용 상황 중 필요한 것만 자연스럽게 질문하세요.
한국어 존댓말로 친절하고 간결하게 답하세요."""


class AIProviderError(Exception):
    pass


def _profile_context(user):
    profile = getattr(user, "profile", None)
    if not profile:
        return {}
    return {
        "nickname": profile.nickname,
        "preferred_categories": profile.preferred_categories,
        "lifestyle": profile.lifestyle,
        "min_budget": profile.min_budget,
        "max_budget": profile.max_budget,
    }


def generate_chat_reply(*, session, user, candidates):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise AIProviderError("OPENAI_API_KEY가 설정되지 않았습니다.")

    history = list(
        session.messages.order_by("created_at").values("role", "content")
    )[-16:]
    reference = {
        "user_profile": _profile_context(user),
        "retrieved_mcm_products": candidates,
    }
    instructions = (
        SYSTEM_PROMPT
        + "\n\n이번 답변에 사용할 조회 결과(JSON):\n"
        + json.dumps(reference, ensure_ascii=False)
    )

    try:
        response = OpenAI(
            api_key=api_key,
            timeout=float(os.getenv("OPENAI_TIMEOUT_SECONDS", "30")),
        ).responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            instructions=instructions,
            input=history,
            max_output_tokens=int(os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "500")),
        )
    except Exception as exc:
        raise AIProviderError("AI 상담 API 호출에 실패했습니다.") from exc

    answer = (response.output_text or "").strip()
    if not answer:
        raise AIProviderError("AI가 빈 응답을 반환했습니다.")
    return answer


def generate_care_reply(context):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise AIProviderError("OPENAI_API_KEY가 설정되지 않았습니다.")

    instructions = """당신은 명품 가방 케어 상담사입니다.
제공된 진단 결과만 근거로 안전한 관리 방법을 한국어로 제안하세요.
확실하지 않으면 공식 AS 상담을 권하고 화학약품 사용을 단정하지 마세요."""
    try:
        response = OpenAI(
            api_key=api_key,
            timeout=float(os.getenv("OPENAI_TIMEOUT_SECONDS", "30")),
        ).responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            instructions=instructions,
            input=json.dumps(context, ensure_ascii=False),
            max_output_tokens=int(os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "500")),
        )
    except Exception as exc:
        raise AIProviderError("AI 케어 API 호출에 실패했습니다.") from exc

    answer = (response.output_text or "").strip()
    if not answer:
        raise AIProviderError("AI가 빈 응답을 반환했습니다.")
    return answer

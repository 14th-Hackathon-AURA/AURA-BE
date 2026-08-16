import base64
import mimetypes
import os
from enum import Enum

from openai import OpenAI
from pydantic import BaseModel, Field, model_validator


DIAGNOSIS_SYSTEM_PROMPT = """당신은 명품 가방의 외관 상태를 확인하는 AURA 이미지 분석 도우미입니다.
업로드된 사진에서 실제로 보이는 정보만 근거로 답하세요.
브랜드 진품 여부, 내부 구조, 냄새, 촉감, 사진 밖의 상태는 추측하지 마세요.

상태 등급은 아래 세 단계만 사용하세요.
- SAFE: 뚜렷한 손상이 보이지 않거나 가벼운 사용 흔적만 보임
- CAUTION: 얼룩, 변색, 가벼운 마모·스크래치처럼 관리가 필요한 손상이 보임
- DANGER: 찢어짐, 갈라짐, 연결 부위 파손처럼 사용 중 추가 손상 위험이 있어 공식 점검이 권장됨

손상 위치는 사진 좌측 상단을 (0, 0), 우측 하단을 (100, 100)으로 보고 가장 중요한 곳만 최대 2개 표시하세요.
관리 제안은 마른 부드러운 천 사용, 습기·열·직사광선 회피처럼 보수적인 내용으로 작성하세요.
강한 세제, 알코올, 임의 염색·접착·수선을 권하지 마세요.
사진 판독은 참고용이며 확실하지 않거나 위험 등급이면 공식 AS 점검을 권하세요.
한국어로 짧고 명확하게 작성하세요."""


class DiagnosisProviderError(Exception):
    pass


class ConditionLevel(str, Enum):
    SAFE = "SAFE"
    CAUTION = "CAUTION"
    DANGER = "DANGER"


class DamagePoint(BaseModel):
    label: str = Field(min_length=1, max_length=40)
    x_percent: float = Field(ge=0, le=100)
    y_percent: float = Field(ge=0, le=100)


class DamageAnalysis(BaseModel):
    condition_level: ConditionLevel
    damage_type: str = Field(max_length=80)
    damage_description: str = Field(min_length=1, max_length=500)
    care_suggestion: str = Field(min_length=1, max_length=500)
    damage_locations: list[DamagePoint] = Field(default_factory=list, max_length=2)

    @model_validator(mode="after")
    def validate_safe_result(self):
        if self.condition_level == ConditionLevel.SAFE:
            self.damage_locations = []
        return self


def _encode_diagnosis_image(diagnosis):
    image = diagnosis.image
    mime_type = mimetypes.guess_type(image.name)[0] or "image/jpeg"
    if not mime_type.startswith("image/"):
        raise DiagnosisProviderError("이미지 형식을 확인할 수 없습니다.")

    try:
        image.open("rb")
        encoded = base64.b64encode(image.read()).decode("ascii")
    except (OSError, ValueError) as exc:
        raise DiagnosisProviderError("진단 이미지를 읽을 수 없습니다.") from exc
    finally:
        image.close()

    return f"data:{mime_type};base64,{encoded}"


def _product_context(product):
    metadata = product.metadata if isinstance(product.metadata, dict) else {}
    return {
        "name": product.name,
        "brand": product.brand,
        "category": product.category,
        "material": metadata.get("material", ""),
    }


def analyze_diagnosis_image(diagnosis):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise DiagnosisProviderError("OPENAI_API_KEY가 설정되지 않았습니다.")

    image_url = _encode_diagnosis_image(diagnosis)
    product = _product_context(diagnosis.product)
    prompt = (
        "다음 제품 사진을 외관 손상 관점에서 분석하세요. "
        f"제품 정보: {product}"
    )

    try:
        response = OpenAI(
            api_key=api_key,
            timeout=float(os.getenv("OPENAI_TIMEOUT_SECONDS", "30")),
        ).responses.parse(
            model=os.getenv(
                "OPENAI_VISION_MODEL",
                os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            ),
            instructions=DIAGNOSIS_SYSTEM_PROMPT,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {
                            "type": "input_image",
                            "image_url": image_url,
                            "detail": "high",
                        },
                    ],
                }
            ],
            text_format=DamageAnalysis,
            max_output_tokens=int(
                os.getenv("OPENAI_VISION_MAX_OUTPUT_TOKENS", "700")
            ),
        )
    except Exception as exc:
        raise DiagnosisProviderError("손상 진단 API 호출에 실패했습니다.") from exc

    analysis = response.output_parsed
    if analysis is None:
        raise DiagnosisProviderError("손상 진단 결과를 해석할 수 없습니다.")

    locations = [point.model_dump() for point in analysis.damage_locations]
    return {
        "condition_level": analysis.condition_level.value,
        "damage_type": analysis.damage_type.strip(),
        "damage_description": analysis.damage_description.strip(),
        "care_suggestion": analysis.care_suggestion.strip(),
        "damage_location": {"points": locations},
        "result": {
            "analysis_method": "ZERO_SHOT_MULTIMODAL",
            "damage_count": len(locations),
            "is_reference_only": True,
            "notice": (
                "사진 기반 AI 분석은 참고용이며 촬영 각도와 조명에 따라 "
                "결과가 달라질 수 있습니다. 정확한 점검은 공식 AS 센터를 이용해 주세요."
            ),
        },
    }

import os
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.core.files.base import ContentFile
from django.test import SimpleTestCase

from .diagnosis_services import (
    ConditionLevel,
    DamageAnalysis,
    DamagePoint,
    DiagnosisProviderError,
    analyze_diagnosis_image,
)


class DiagnosisServiceTests(SimpleTestCase):
    def diagnosis(self):
        return SimpleNamespace(
            image=ContentFile(b"fake-image", name="bag.jpg"),
            product=SimpleNamespace(
                name="MCM 가방",
                brand="MCM",
                category="bag",
                metadata={"material": "코팅 캔버스"},
            ),
        )

    @patch.dict(
        os.environ,
        {
            "OPENAI_API_KEY": "test-key",
            "OPENAI_VISION_MODEL": "gpt-4.1-mini",
        },
        clear=False,
    )
    @patch("apps.care.diagnosis_services.OpenAI")
    def test_returns_validated_structured_analysis(self, openai_mock):
        parsed = DamageAnalysis(
            condition_level=ConditionLevel.CAUTION,
            damage_type="모서리 마모",
            damage_description="하단 모서리에 마모가 보입니다.",
            care_suggestion="마른 천으로 닦고 공식 점검을 고려해 주세요.",
            damage_locations=[
                DamagePoint(label="하단 모서리", x_percent=82, y_percent=91)
            ],
        )
        client = Mock()
        client.responses.parse.return_value = SimpleNamespace(output_parsed=parsed)
        openai_mock.return_value = client

        result = analyze_diagnosis_image(self.diagnosis())

        self.assertEqual(result["condition_level"], "CAUTION")
        self.assertEqual(result["result"]["damage_count"], 1)
        self.assertTrue(result["result"]["is_reference_only"])
        request = client.responses.parse.call_args.kwargs
        self.assertEqual(request["model"], "gpt-4.1-mini")
        image_input = request["input"][0]["content"][1]
        self.assertTrue(image_input["image_url"].startswith("data:image/jpeg;base64,"))

    @patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False)
    def test_missing_api_key_is_provider_error(self):
        with self.assertRaises(DiagnosisProviderError):
            analyze_diagnosis_image(self.diagnosis())

    def test_safe_result_removes_damage_markers(self):
        parsed = DamageAnalysis(
            condition_level=ConditionLevel.SAFE,
            damage_type="",
            damage_description="뚜렷한 손상이 보이지 않습니다.",
            care_suggestion="통풍이 잘되는 곳에 보관해 주세요.",
            damage_locations=[
                DamagePoint(label="사용 흔적", x_percent=40, y_percent=40)
            ],
        )

        self.assertEqual(parsed.damage_locations, [])

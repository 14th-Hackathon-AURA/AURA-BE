from unittest.mock import patch

from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from apps.accounts.models import Profile

from .catalog import get_product, load_catalog, recommend_products
from .models import ChatMessage, ChatSession, VisitCard
from .services import (
    VISIT_CARD_SUMMARY_MAX_LENGTH,
    VISIT_CARD_SUMMARY_FALLBACK,
    generate_visit_card_summary,
)


class ProductCatalogTests(APITestCase):
    def test_catalog_contains_received_products_and_only_public_fields(self):
        products = load_catalog()

        self.assertEqual(len(products), 94)
        self.assertTrue(all(product["style_code"] for product in products))
        self.assertNotIn("product_url", products[0])
        self.assertNotIn("official_description", products[0])

    def test_recommendation_uses_budget_and_usage(self):
        products = recommend_products(
            "200만원 이하 출근용 가방 추천해줘",
            limit=3,
        )

        self.assertTrue(products)
        self.assertTrue(all(item["price_value"] <= 2_000_000 for item in products))
        self.assertTrue(
            any(
                "출근" in item["usage"]
                or "비즈니스" in item["usage"]
                or "오피스" in item["style"]
                for item in products
            )
        )


class ChatApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="chat@example.com",
            email="chat@example.com",
            password="strong-pass-123",
        )
        Profile.objects.create(
            user=self.user,
            nickname="아기사자",
            preferred_categories=["가방"],
            lifestyle=["출근"],
            min_budget=500_000,
            max_budget=2_000_000,
        )
        self.client.force_authenticate(self.user)

    @patch("apps.ai.views.generate_chat_reply", return_value="조건에 맞는 상품을 찾았어요.")
    def test_chat_persists_messages_and_returns_retrieved_products(self, mock_reply):
        response = self.client.post(
            "/api/ai/chat/",
            {"message": "200만원 이하 출근용 가방 추천해줘"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["answer"], "조건에 맞는 상품을 찾았어요.")
        self.assertGreater(len(response.data["recommended_products"]), 0)
        self.assertLessEqual(len(response.data["recommended_products"]), 3)
        self.assertIsNone(response.data["visit_card"])

        session = ChatSession.objects.get(id=response.data["session_id"])
        self.assertEqual(session.messages.count(), 2)
        self.assertEqual(
            list(session.messages.values_list("role", flat=True)),
            [ChatMessage.Role.USER, ChatMessage.Role.ASSISTANT],
        )
        self.assertEqual(
            session.last_recommendation_codes[0],
            response.data["recommended_products"][0]["style_code"],
        )
        mock_reply.assert_called_once()

    @patch(
        "apps.ai.views.generate_visit_card_summary",
        return_value=(
            "아기사자님이 데이트용으로 원하신 가방입니다. "
            "선택한 상품의 스타일과 사용 상황이 요청하신 조건에 어울립니다."
        ),
    )
    @patch("apps.ai.views.generate_chat_reply", return_value="추천 결과입니다.")
    def test_chat_saves_last_recommendation_as_visit_card(
        self,
        mock_reply,
        mock_summary,
    ):
        recommendation = self.client.post(
            "/api/ai/chat/",
            {"message": "데이트용 가방 추천해줘"},
            format="json",
        )
        session_id = recommendation.data["session_id"]
        product = recommendation.data["recommended_products"][0]

        saved = self.client.post(
            "/api/ai/chat/",
            {
                "session_id": session_id,
                "message": "이 제품 카드로 저장해줘",
                "product_code": product["style_code"],
            },
            format="json",
        )

        self.assertEqual(saved.status_code, 200)
        self.assertEqual(saved.data["visit_card"]["style_code"], product["style_code"])
        summary = saved.data["visit_card"]["consultation_summary"]
        self.assertIn("아기사자님이 데이트용으로 원하신 가방", summary)
        self.assertNotIn("추천 결과입니다.", summary)
        self.assertNotIn("http", summary)
        self.assertNotIn("**", summary)
        self.assertEqual(VisitCard.objects.filter(user=self.user).count(), 1)

        saved_again = self.client.post(
            "/api/ai/chat/",
            {
                "session_id": session_id,
                "message": "이 추천 카드로 다시 저장해줘",
                "product_code": product["style_code"],
            },
            format="json",
        )
        self.assertEqual(saved_again.status_code, 200)
        self.assertEqual(VisitCard.objects.filter(user=self.user).count(), 1)
        self.assertEqual(
            saved_again.data["visit_card"]["consultation_summary"],
            summary,
        )

        card = VisitCard.objects.get(user=self.user)
        self.assertEqual(card.consultation_summary, summary)
        self.assertEqual(mock_summary.call_count, 2)

    @patch(
        "apps.ai.serializers.generate_visit_card_summary",
        return_value=(
            "아기사자님이 출근할 때 사용할 검은색 가방입니다. "
            "선택한 상품은 요청하신 사용 상황에 적합합니다."
        ),
    )
    def test_direct_visit_card_uses_server_generated_summary(self, mock_summary):
        product = load_catalog()[0]
        session = ChatSession.objects.create(user=self.user)
        ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.USER,
            content="출근할 때 쓸 검은색 가방을 추천해줘",
        )

        response = self.client.post(
            "/api/ai/visit-cards/",
            {
                "session_id": session.id,
                "style_code": product["style_code"],
                "consultation_summary": "프론트에서 보낸 임의의 전체 답변",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertIn("출근할 때 사용할 검은색 가방", response.data["consultation_summary"])
        self.assertNotIn("프론트에서 보낸 임의의 전체 답변", response.data["consultation_summary"])
        mock_summary.assert_called_once()

    @patch.dict("os.environ", {"OPENAI_API_KEY": ""})
    def test_visit_card_summary_uses_fallback_when_generation_fails(self):
        product = load_catalog()[0]
        session = ChatSession.objects.create(user=self.user)

        summary = generate_visit_card_summary(
            session=session,
            user=self.user,
            product=product,
        )

        self.assertEqual(
            summary,
            "상담 요약을 생성하지 못했습니다. 잠시 후 카드를 다시 저장해 주세요.",
        )
        self.assertEqual(summary, VISIT_CARD_SUMMARY_FALLBACK)

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    @patch("apps.ai.services.OpenAI")
    def test_visit_card_summary_rejects_more_than_300_characters(
        self,
        openai_mock,
    ):
        product = load_catalog()[0]
        session = ChatSession.objects.create(user=self.user)
        openai_mock.return_value.responses.create.return_value.output_text = (
            "가" * (VISIT_CARD_SUMMARY_MAX_LENGTH + 1)
        )

        summary = generate_visit_card_summary(
            session=session,
            user=self.user,
            product=product,
        )

        self.assertEqual(summary, VISIT_CARD_SUMMARY_FALLBACK)

    def test_visit_cards_are_private(self):
        product = get_product(load_catalog()[0]["style_code"])
        VisitCard.objects.create(
            user=self.user,
            style_code=product["style_code"],
            product=product,
        )
        other = User.objects.create_user("other", password="strong-pass-123")
        VisitCard.objects.create(
            user=other,
            style_code=load_catalog()[1]["style_code"],
            product=load_catalog()[1],
        )

        response = self.client.get("/api/ai/visit-cards/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["style_code"], product["style_code"])

    def test_cannot_save_chat_card_before_recommendation(self):
        session = ChatSession.objects.create(user=self.user)

        response = self.client.post(
            "/api/ai/chat/",
            {"session_id": session.id, "message": "카드로 저장해줘"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(session.messages.count(), 0)

    @patch.dict("os.environ", {"OPENAI_API_KEY": ""})
    def test_chat_returns_503_when_api_key_is_missing(self):
        response = self.client.post(
            "/api/ai/chat/",
            {"message": "가방 추천해줘"},
            format="json",
        )

        self.assertEqual(response.status_code, 503)

    @patch("apps.ai.views.generate_chat_reply", return_value="대화를 이어갈게요.")
    def test_chat_cannot_access_another_users_session(self, mock_reply):
        other = User.objects.create_user("other", password="strong-pass-123")
        other_session = ChatSession.objects.create(user=other)

        response = self.client.post(
            "/api/ai/chat/",
            {"session_id": other_session.id, "message": "계속 상담해줘"},
            format="json",
        )

        self.assertEqual(response.status_code, 404)
        mock_reply.assert_not_called()

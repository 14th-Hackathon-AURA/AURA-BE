from django.contrib.auth.models import User
from rest_framework.test import APITestCase


class AccountApiTests(APITestCase):
    def test_register_login_with_email_and_update_profile(self):
        response = self.client.post(
            "/api/auth/register/",
            {"email": "aura@example.com", "password": "strong-pass-123"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)

        response = self.client.post(
            "/api/auth/token/",
            {"email": "aura@example.com", "password": "strong-pass-123"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

        response = self.client.patch(
            "/api/me/",
            {
                "nickname": "아기사자",
                "gender": "FEMALE",
                "age_range": "20대 중후반",
                "preferred_categories": ["핸드백", "액세서리"],
                "lifestyle": ["직장", "여행"],
                "min_budget": 1000000,
                "max_budget": 3000000,
                "onboarding_completed": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], "aura@example.com")
        self.assertEqual(response.data["membership_tier"], "AURA Silver")

    def test_budget_range_validation(self):
        user = User.objects.create_user("user", password="strong-pass-123")
        self.client.force_authenticate(user)
        response = self.client.patch(
            "/api/me/", {"min_budget": 300, "max_budget": 100}, format="json"
        )
        self.assertEqual(response.status_code, 400)

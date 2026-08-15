from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from apps.care.models import Diagnosis, Store, VisitReservation
from apps.catalog.models import Product
from apps.community.models import Comment, Post

from .models import Notification


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
                "lifestyle": ["직장", "여행"],
                "onboarding_completed": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], "aura@example.com")
        self.assertEqual(response.data["membership_tier"], "AURA Silver")
        self.assertNotIn("membership_points", response.data)

    def test_budget_range_validation(self):
        user = User.objects.create_user("user", password="strong-pass-123")
        self.client.force_authenticate(user)
        response = self.client.patch(
            "/api/me/", {"min_budget": 300, "max_budget": 100}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_diagnosis_and_visit_events_create_notifications_once(self):
        user = User.objects.create_user("events", password="strong-pass-123")
        product = Product.objects.create(user=user, name="Bag", category="bag")
        diagnosis = Diagnosis.objects.create(
            product=product,
            requested_by=user,
            image="diagnoses/test.jpg",
        )
        diagnosis.status = Diagnosis.Status.DONE
        diagnosis.condition_level = Diagnosis.ConditionLevel.CAUTION
        diagnosis.save()
        diagnosis.save()

        store = Store.objects.create(
            name="청담 플래그십",
            address="서울",
            phone="02-0000-0000",
        )
        visit = VisitReservation.objects.create(
            user=user,
            store=store,
            visit_at="2026-08-20T10:00:00+09:00",
            purpose="제품 상담",
            reservation_code="AURA1234",
        )

        notifications = Notification.objects.filter(user=user)
        self.assertEqual(notifications.count(), 2)
        self.assertEqual(
            notifications.get(event_key=f"diagnosis:{diagnosis.id}:done").action_url,
            f"/care/diagnoses/{diagnosis.id}",
        )
        self.assertEqual(
            notifications.get(event_key=f"visit:{visit.id}:created").action_url,
            f"/my/visit-reservations/{visit.id}",
        )

    def test_membership_upgrade_creates_notification(self):
        user = User.objects.create_user("member", password="strong-pass-123")
        posts = Post.objects.bulk_create(
            [Post(author=user, title=f"post-{index}", body="") for index in range(50)]
        )
        Comment.objects.bulk_create(
            [Comment(post=posts[0], author=user, body="comment") for _ in range(49)]
        )
        Comment.objects.create(post=posts[0], author=user, body="50번째 댓글")

        notification = Notification.objects.get(
            user=user, event_key="membership:AURA Gold"
        )
        self.assertEqual(notification.type, Notification.Type.MEMBERSHIP)
        self.assertEqual(notification.action_url, "/my/membership")

import base64
from unittest.mock import patch
from datetime import datetime, time, timedelta
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.catalog.models import Product
from .diagnosis_services import DiagnosisProviderError
from .models import CareGuide, Diagnosis, Store, VisitReservation


class DiagnosisApiTests(APITestCase):
    image_bytes = base64.b64decode(
        "R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw=="
    )
    def setUp(self):
        self.user = User.objects.create_user("owner", password="strong-pass-123")
        self.other = User.objects.create_user("other", password="strong-pass-123")
        self.product = Product.objects.create(user=self.user, name="Bag", category="bag")
        self.other_product = Product.objects.create(user=self.other, name="Other", category="bag")
        self.client.force_authenticate(self.user)

    @staticmethod
    def analysis_result():
        return {
            "condition_level": "CAUTION",
            "damage_type": "표면 얼룩",
            "damage_description": "가방 전면에 옅은 얼룩이 보입니다.",
            "care_suggestion": "마른 부드러운 천으로 가볍게 닦아 주세요.",
            "damage_location": {
                "points": [
                    {
                        "label": "전면 얼룩",
                        "x_percent": 48.0,
                        "y_percent": 55.0,
                    }
                ]
            },
            "result": {
                "analysis_method": "ZERO_SHOT_MULTIMODAL",
                "damage_count": 1,
                "is_reference_only": True,
            },
        }

    @patch("apps.care.views.analyze_diagnosis_image")
    def test_create_analyzes_and_filters_diagnosis(self, analyze_mock):
        analyze_mock.return_value = self.analysis_result()
        image = SimpleUploadedFile("damage.gif", self.image_bytes, content_type="image/gif")
        response = self.client.post(
            "/api/diagnoses/", {"product": self.product.id, "image": image}, format="multipart"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], Diagnosis.Status.DONE)
        self.assertEqual(response.data["condition_level"], Diagnosis.ConditionLevel.CAUTION)
        self.assertEqual(response.data["result"]["damage_count"], 1)
        response = self.client.get(
            "/api/diagnoses/", {"product": self.product.id, "year": timezone.now().year}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    @patch("apps.care.views.analyze_diagnosis_image")
    def test_provider_failure_marks_diagnosis_failed(self, analyze_mock):
        analyze_mock.side_effect = DiagnosisProviderError("provider failed")
        image = SimpleUploadedFile("damage.gif", self.image_bytes, content_type="image/gif")

        response = self.client.post(
            "/api/diagnoses/", {"product": self.product.id, "image": image}, format="multipart"
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], Diagnosis.Status.FAILED)
        self.assertNotIn("provider failed", str(response.data["result"]))

    def test_cannot_diagnose_other_users_product(self):
        image = SimpleUploadedFile("damage.gif", self.image_bytes, content_type="image/gif")
        response = self.client.post(
            "/api/diagnoses/", {"product": self.other_product.id, "image": image}, format="multipart"
        )
        self.assertEqual(response.status_code, 400)

    def test_invalid_year_is_validation_error(self):
        self.assertEqual(self.client.get("/api/diagnoses/", {"year": "bad"}).status_code, 400)

    @patch("apps.care.views.analyze_diagnosis_image")
    def test_owner_can_update_reanalyze_and_delete_diagnosis(self, analyze_mock):
        analyze_mock.return_value = self.analysis_result()
        diagnosis = Diagnosis.objects.create(
            product=self.product,
            requested_by=self.user,
            image=SimpleUploadedFile("before.gif", self.image_bytes, content_type="image/gif"),
        )
        replacement = SimpleUploadedFile("after.gif", self.image_bytes, content_type="image/gif")
        response = self.client.patch(
            f"/api/diagnoses/{diagnosis.id}/", {"image": replacement}, format="multipart"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], Diagnosis.Status.DONE)
        analyze_mock.assert_called_once()
        self.assertEqual(self.client.delete(f"/api/diagnoses/{diagnosis.id}/").status_code, 204)

    @patch("apps.care.views.analyze_diagnosis_image")
    def test_update_without_image_or_product_change_does_not_reanalyze(self, analyze_mock):
        diagnosis = Diagnosis.objects.create(
            product=self.product,
            requested_by=self.user,
            image=SimpleUploadedFile(
                "before.gif",
                self.image_bytes,
                content_type="image/gif",
            ),
            status=Diagnosis.Status.DONE,
            condition_level=Diagnosis.ConditionLevel.SAFE,
        )

        response = self.client.patch(
            f"/api/diagnoses/{diagnosis.id}/",
            {"product": self.product.id},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], Diagnosis.Status.DONE)
        self.assertEqual(
            response.data["condition_level"],
            Diagnosis.ConditionLevel.SAFE,
        )
        analyze_mock.assert_not_called()

    def test_other_user_cannot_update_or_delete_diagnosis(self):
        diagnosis = Diagnosis.objects.create(
            product=self.other_product,
            requested_by=self.other,
            image=SimpleUploadedFile("other.gif", self.image_bytes, content_type="image/gif"),
        )
        self.assertEqual(
            self.client.patch(f"/api/diagnoses/{diagnosis.id}/", {"product": self.product.id}).status_code,
            404,
        )
        self.assertEqual(self.client.delete(f"/api/diagnoses/{diagnosis.id}/").status_code, 404)

    def test_care_guides_filter_by_final_screen_type(self):
        CareGuide.objects.create(
            title="구매 직후 체크리스트",
            guide_type=CareGuide.GuideType.POST_PURCHASE,
            material="가죽",
            content="보증서와 영수증을 보관해 주세요.",
        )
        CareGuide.objects.create(
            title="사후 케어",
            guide_type=CareGuide.GuideType.AFTER_CARE,
            material="가죽",
            content="사용 후 마른 천으로 닦아 주세요.",
        )
        response = self.client.get(
            "/api/care-guides/", {"guide_type": "POST_PURCHASE"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["guide_type"], "POST_PURCHASE")

    def test_service_request_cannot_use_another_users_reservation(self):
        store = Store.objects.create(
            name="청담 플래그십", address="서울", phone="02-0000-0000"
        )
        other_reservation = VisitReservation.objects.create(
            user=self.other,
            store=store,
            product=self.other_product,
            visit_at="2026-08-20T10:00:00+09:00",
            purpose="상담",
            reservation_code="OTHER123",
        )
        response = self.client.post(
            "/api/service-requests/",
            {
                "product": self.product.id,
                "store": store.id,
                "reservation": other_reservation.id,
                "symptom": "표면 오염",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("reservation", response.data)

class ReservationStoreSelectionApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="reservation-owner",
            password="strong-pass-123",
        )
        self.product = Product.objects.create(
            user=self.user,
            name="MCM Bag",
            category="bag",
        )

        self.near_store = Store.objects.create(
            name="가까운 MCM 매장",
            address="서울특별시 강남구",
            phone="02-1111-1111",
            sido="서울특별시",
            sigungu="강남구",
            store_type="플래그십",
            latitude="37.5180000",
            longitude="127.0480000",
            opening_hours="매일 10:00-18:00",
            supports_as=True,
        )
        self.far_store = Store.objects.create(
            name="먼 MCM 매장",
            address="서울특별시 송파구",
            phone="02-2222-2222",
            sido="서울특별시",
            sigungu="송파구",
            store_type="백화점",
            latitude="37.5100000",
            longitude="127.1100000",
            opening_hours="매일 10:00-18:00",
            supports_as=True,
        )

        self.client.force_authenticate(self.user)

    def future_visit_at(self):
        selected_date = timezone.localdate() + timedelta(days=1)

        return timezone.make_aware(
            datetime.combine(
                selected_date,
                time(10, 0),
            )
        )

    def test_nearby_stores_are_returned_in_distance_order(self):
        response = self.client.get(
            "/api/stores/",
            {
                "latitude": "37.5172",
                "longitude": "127.0473",
                "limit": "2",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        self.assertTrue(response.data["location_used"])
        self.assertEqual(
            response.data["stores"][0]["id"],
            self.near_store.id,
        )
        self.assertIsNotNone(
            response.data["stores"][0]["distance_km"]
        )

    def test_store_search_filters_reservation_options(self):
        response = self.client.get(
            "/api/stores/",
            {"q": "강남"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["stores"][0]["id"],
            self.near_store.id,
        )

    def test_create_reservation_with_selected_store(self):
        visit_at = self.future_visit_at()

        response = self.client.post(
            "/api/visit-reservations/",
            {
                "product": self.product.id,
                "store": self.near_store.id,
                "visit_at": visit_at.isoformat(),
                "purpose": "제품 상태 점검",
                "contact_name": "홍길동",
                "contact_phone": "010-1234-5678",
                "request_note": "방문 전 연락 부탁드립니다.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.data["store"],
            self.near_store.id,
        )
        self.assertEqual(
            response.data["store_detail"]["id"],
            self.near_store.id,
        )
        self.assertEqual(
            response.data["store_detail"]["name"],
            self.near_store.name,
        )
        self.assertEqual(
            response.data["status"],
            VisitReservation.Status.RESERVED,
        )

    def test_availability_contains_selected_store_detail(self):
        selected_date = (
            timezone.localdate() + timedelta(days=1)
        )

        response = self.client.get(
            "/api/visit-reservations/availability/",
            {
                "store": self.near_store.id,
                "date": selected_date.isoformat(),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["store"]["id"],
            self.near_store.id,
        )
        self.assertEqual(
            response.data["store"]["address"],
            self.near_store.address,
        )
        self.assertIn("slots", response.data)

    def test_reservation_requires_store(self):
        response = self.client.post(
            "/api/visit-reservations/",
            {
                "product": self.product.id,
                "visit_at": self.future_visit_at().isoformat(),
                "purpose": "제품 상태 점검",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("store", response.data)
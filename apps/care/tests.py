import base64
from unittest.mock import patch

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

import base64

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.catalog.models import Product
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

    def test_create_and_filter_diagnosis(self):
        image = SimpleUploadedFile("damage.gif", self.image_bytes, content_type="image/gif")
        response = self.client.post(
            "/api/diagnoses/", {"product": self.product.id, "image": image}, format="multipart"
        )
        self.assertEqual(response.status_code, 201)
        response = self.client.get(
            "/api/diagnoses/", {"product": self.product.id, "year": timezone.now().year}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_cannot_diagnose_other_users_product(self):
        image = SimpleUploadedFile("damage.gif", self.image_bytes, content_type="image/gif")
        response = self.client.post(
            "/api/diagnoses/", {"product": self.other_product.id, "image": image}, format="multipart"
        )
        self.assertEqual(response.status_code, 400)

    def test_invalid_year_is_validation_error(self):
        self.assertEqual(self.client.get("/api/diagnoses/", {"year": "bad"}).status_code, 400)

    def test_owner_can_update_and_delete_diagnosis(self):
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

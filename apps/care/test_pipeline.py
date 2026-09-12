from datetime import timedelta
from io import BytesIO
import os
from pathlib import Path
import tempfile
import uuid
from unittest.mock import patch

from PIL import Image
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.test import APITestCase

from apps.catalog.models import Product
from .diagnosis_jobs import run_diagnosis
from .diagnosis_services import DiagnosisProviderError, review_result
from .image_utils import normalize_upload
from .models import Diagnosis
from .yolo_diagnosis import build_result, analyze_yolo, CLASS_NAMES


def photo(exif=False):
    stream = BytesIO()
    image = Image.new("RGB", (80, 40), "brown")
    metadata = Image.Exif()
    if exif:
        metadata[274] = 6
    image.save(stream, format="JPEG", exif=metadata)
    return SimpleUploadedFile("bag.jpg", stream.getvalue(), content_type="image/jpeg")


class ImagePipelineTests(SimpleTestCase):
    def test_exif_is_applied_and_stripped(self):
        output = normalize_upload(photo(exif=True))
        with Image.open(output) as image:
            self.assertEqual(image.size, (40, 80))
            self.assertEqual(dict(image.getexif()), {})

    def test_fake_file_rejected(self):
        with self.assertRaises(ValidationError):
            normalize_upload(SimpleUploadedFile("bad.jpg", b"not a photo"))

    def test_oversized_file_rejected(self):
        upload = photo()
        upload.size = 11 * 1024 * 1024
        with self.assertRaises(ValidationError):
            normalize_upload(upload)

    def test_animation_rejected(self):
        out = BytesIO()
        Image.new("RGB", (10, 10), "red").save(out, format="GIF", save_all=True,
            append_images=[Image.new("RGB", (10, 10), "blue")], duration=100, loop=0)
        with self.assertRaises(ValidationError):
            normalize_upload(SimpleUploadedFile("movie.gif", out.getvalue()))


class DetectorTests(SimpleTestCase):
    def test_empty_detections_are_not_safe(self):
        result = build_result([], "sha256")
        self.assertEqual(result["condition_level"], "")
        self.assertTrue(result["result"]["requires_review"])

    def test_box_coordinate_contract(self):
        result = build_result([(3, .82, [.1, .2, .5, .6])], "version")
        self.assertEqual(result["damage_location"]["boxes"][0]["width_percent"], 40)
        self.assertEqual(result["damage_location"]["points"][0]["x_percent"], 30)
        self.assertEqual(result["damage_location"]["points"][0]["y_percent"], 40)
        self.assertEqual(result["condition_level"], "CAUTION")

    def test_invalid_model_output_rejected(self):
        for row in [(99, .5, [0, 0, 1, 1]), (1, float("nan"), [0, 0, 1, 1]), (0, .7, [.5, .5, .4, .4])]:
            with self.assertRaises(DiagnosisProviderError):
                build_result([row], "version")

    def test_schema_matches_training(self):
        from ml.schema import CLASS_NAMES as training_names
        self.assertEqual(CLASS_NAMES, training_names)

    def test_missing_weights_no_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.dict(os.environ, {"AURA_YOLO_WEIGHTS": str(Path(folder) / "missing.pt")}):
                with self.assertRaises(DiagnosisProviderError) as error:
                    analyze_yolo(None)
                self.assertEqual(error.exception.code, "MODEL_NOT_READY")


@override_settings(DIAGNOSIS_EXECUTION="database")
class AsyncDiagnosisTests(APITestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.media = override_settings(MEDIA_ROOT=self.folder.name)
        self.media.enable()
        self.addCleanup(self.folder.cleanup)
        self.addCleanup(self.media.disable)
        cache.clear()
        self.user = User.objects.create_user("pipeline-owner")
        self.other = User.objects.create_user("pipeline-other")
        self.product = Product.objects.create(user=self.user, name="가방", category="bag")
        self.client.force_authenticate(self.user)

    def create(self):
        response = self.client.post("/api/diagnoses/", {"product": self.product.id, "image": photo()}, format="multipart")
        self.assertEqual(response.status_code, 201, response.data)
        return Diagnosis.objects.get(pk=response.data["id"])

    def test_pending_then_worker_finishes(self):
        d = self.create()
        self.assertEqual(d.status, "PENDING")
        self.assertTrue(run_diagnosis(d, analyzer=lambda _: review_result("확인 필요", "TEST")))
        result = self.client.get(f"/api/diagnoses/{d.pk}/").data
        self.assertEqual(result["status"], "DONE")
        self.assertEqual(result["condition_label"], "판독 보류")
        self.assertNotIn("lease_token", result)
        self.assertIsNotNone(result["completed_at"])

    def test_replacement_photo_invalidates_running_result(self):
        d = self.create()
        def late_result(_):
            response = self.client.patch(f"/api/diagnoses/{d.pk}/", {"image": photo()}, format="multipart")
            self.assertEqual(response.status_code, 200)
            return review_result("OLD RESULT", "TEST")
        self.assertFalse(run_diagnosis(d, analyzer=late_result))
        d.refresh_from_db()
        self.assertEqual(d.status, "PENDING")
        self.assertEqual(d.result, {})
        self.assertTrue(run_diagnosis(d, analyzer=lambda _: review_result("NEW RESULT", "TEST")))
        d.refresh_from_db()
        self.assertEqual(d.damage_description, "NEW RESULT")

    def test_live_lease_not_claimed_twice(self):
        d = self.create()
        def analysis(_):
            self.assertFalse(run_diagnosis(d, analyzer=lambda _: self.fail("duplicate call")))
            return review_result("done", "TEST")
        self.assertTrue(run_diagnosis(d, analyzer=analysis))

    def test_expired_worker_lease_is_recovered(self):
        d = self.create()
        Diagnosis.objects.filter(pk=d.pk).update(lease_token=uuid.uuid4(), lease_expires_at=timezone.now()-timedelta(seconds=1))
        self.assertTrue(run_diagnosis(d, analyzer=lambda _: review_result("recovered", "TEST")))

    @override_settings(DIAGNOSIS_MAX_ATTEMPTS=1)
    def test_crash_attempt_budget(self):
        d = self.create()
        Diagnosis.objects.filter(pk=d.pk).update(analysis_attempts=1)
        self.assertTrue(run_diagnosis(d, analyzer=lambda _: self.fail("must not call")))
        d.refresh_from_db()
        self.assertEqual(d.result["error_code"], "WORKER_TIMEOUT")

    def test_failed_can_retry_only_once(self):
        d = self.create()
        def fail(_):
            raise DiagnosisProviderError("private provider error")
        run_diagnosis(d, analyzer=fail)
        self.assertEqual(self.client.post(f"/api/diagnoses/{d.pk}/retry/").data["status"], "PENDING")
        self.assertEqual(self.client.post(f"/api/diagnoses/{d.pk}/retry/").status_code, 400)

    def test_other_users_history_and_retry_not_visible(self):
        d = self.create()
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(f"/api/diagnoses/{d.pk}/").status_code, 404)
        self.assertEqual(self.client.post(f"/api/diagnoses/{d.pk}/retry/").status_code, 404)
        self.assertEqual(self.client.get("/api/diagnoses/filter-options/").data, {"products": [], "years": []})

    def test_bad_filters(self):
        for query in ["product=bad", "product=-1", "product=9999999999999999999999999", "year=10000", "year=0"]:
            self.assertEqual(self.client.get(f"/api/diagnoses/?{query}").status_code, 400)

    def test_multipart_checklist_saved(self):
        response = self.client.post("/api/diagnoses/", {"product": self.product.id, "image": photo(),
            "checklist": '{"whole_bag_visible": true, "well_lit": true, "unobstructed": true}'}, format="multipart")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(response.data["checklist"]["well_lit"])

    def test_invalid_checklist_rejected(self):
        response = self.client.post("/api/diagnoses/", {"product": self.product.id, "image": photo(),
            "checklist": '{"well_lit": "true"}'}, format="multipart")
        self.assertEqual(response.status_code, 400)

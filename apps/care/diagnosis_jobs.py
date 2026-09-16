"""Small durable DB queue. No background threads inside a web request.

An expiring lease recovers crashed workers; revision + lease token prevents a
late worker from overwriting a replacement photo or a newer retry.
"""
import logging
import uuid
from datetime import timedelta

from django.conf import settings
from django.db.models import F, Q
from django.utils import timezone

from .models import Diagnosis

logger = logging.getLogger(__name__)
RESULT_FIELDS = ("condition_level", "damage_type", "damage_description",
                 "care_suggestion", "damage_location", "result")


def available():
    return Diagnosis.objects.filter(status=Diagnosis.Status.PENDING).filter(
        Q(lease_expires_at__isnull=True) | Q(lease_expires_at__lt=timezone.now())
    )


def run_diagnosis(diagnosis, analyzer=None):
    from .diagnosis_services import DiagnosisProviderError, analyze_diagnosis_image
    analyzer = analyzer or analyze_diagnosis_image
    token = uuid.uuid4()
    claimed = available().filter(pk=diagnosis.pk, analysis_revision=diagnosis.analysis_revision).update(
        lease_token=token,
        lease_expires_at=timezone.now() + timedelta(seconds=settings.DIAGNOSIS_LEASE_SECONDS),
        analysis_attempts=F("analysis_attempts") + 1,
    )
    if not claimed:
        return False
    # Reload only this revision. A concurrent PATCH may already have replaced it.
    current = Diagnosis.objects.select_related("product").filter(
        pk=diagnosis.pk, analysis_revision=diagnosis.analysis_revision, lease_token=token
    ).first()
    if current is None:
        return False
    try:
        if current.analysis_attempts > settings.DIAGNOSIS_MAX_ATTEMPTS:
            raise DiagnosisProviderError("작업 재시도 한도 초과", code="WORKER_TIMEOUT")
        result = analyzer(current)
        values = {key: result[key] for key in RESULT_FIELDS}
        values["status"] = Diagnosis.Status.DONE
    except Exception as exc:
        # Never log image bytes, product metadata or the external provider message.
        code = exc.code if isinstance(exc, DiagnosisProviderError) else "INTERNAL_ERROR"
        logger.warning("Diagnosis %s failed (%s)", current.pk, code)
        values = dict(status=Diagnosis.Status.FAILED, condition_level="", damage_type="",
                      damage_description="", care_suggestion="", damage_location={},
                      result={"error_code": code, "error": "이미지 분석에 실패했습니다. 다시 촬영하거나 잠시 후 재시도해 주세요."})
    changed = Diagnosis.objects.filter(
        pk=current.pk, analysis_revision=current.analysis_revision, lease_token=token
    ).update(**values, lease_token=None, lease_expires_at=None, completed_at=timezone.now())
    return bool(changed)

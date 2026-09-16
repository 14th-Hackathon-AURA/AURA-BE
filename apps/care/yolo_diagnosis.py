"""Optional detector. Requires YOUR reviewed, fine-tuned local weights.

Never download COCO weights at inference or silently fall back to another API.
"""
import hashlib
import math
import os
from functools import lru_cache
from pathlib import Path
from threading import Lock

from PIL import Image
from .diagnosis_schema import DIAGNOSIS_CLASS_CODES
from .diagnosis_services import DiagnosisProviderError, review_result

CLASS_NAMES = list(DIAGNOSIS_CLASS_CODES)
LABELS = ["형태변형", "지퍼·원단 찢어짐", "손잡이 마모·뜯김", "표면 얼룩·오염", "가죽 갈라짐"]
_LOCK = Lock()


@lru_cache(maxsize=1)
def _load_model(path, modified_ns):
    try:
        from ultralytics import YOLO
        model = YOLO(path)
        names = [model.names[i] for i in range(len(model.names))]
        if names != CLASS_NAMES or model.task != "detect":
            raise ValueError("weights do not match AURA class schema")
        digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        return model, digest
    except Exception as exc:
        raise DiagnosisProviderError("AURA 탐지 가중치를 읽을 수 없습니다.", code="MODEL_NOT_READY") from exc


def build_result(detections, digest):
    """detections: class index, score, normalized x1/y1/x2/y2 (not YOLO xywh)."""
    boxes = []
    for class_id, score, xyxy in detections:
        values = [score, *xyxy]
        if class_id not in range(len(CLASS_NAMES)) or not all(math.isfinite(v) for v in values):
            raise DiagnosisProviderError("잘못된 탐지 결과", code="MODEL_OUTPUT_INVALID")
        x1, y1, x2, y2 = [max(0, min(1, float(v))) for v in xyxy]
        if not (0 <= score <= 1 and x1 < x2 and y1 < y2):
            raise DiagnosisProviderError("잘못된 탐지 좌표", code="MODEL_OUTPUT_INVALID")
        boxes.append({"class_id": class_id, "label": LABELS[class_id], "confidence": round(score, 4),
                      "x_percent": round(x1 * 100, 3), "y_percent": round(y1 * 100, 3),
                      "width_percent": round((x2 - x1) * 100, 3), "height_percent": round((y2 - y1) * 100, 3)})
    if not boxes:
        result = review_result("학습된 5개 하자 유형이 검출되지 않았습니다. 정상 여부는 이 결과만으로 확정할 수 없습니다.", "YOLO_DETECTION")
        result["result"]["model_version"] = digest
        return result
    boxes.sort(key=lambda b: b["confidence"], reverse=True)
    points = [{"label": b["label"], "x_percent": b["x_percent"] + b["width_percent"] / 2,
               "y_percent": b["y_percent"] + b["height_percent"] / 2} for b in boxes[:2]]
    labels = list(dict.fromkeys(b["label"] for b in boxes))
    # This is a transparent provisional routing rule, NOT a learned severity score.
    danger = any(b["class_id"] == 1 for b in boxes)
    return {
        "condition_level": "DANGER" if danger else "CAUTION", "damage_type": ", ".join(labels),
        "damage_description": f"사진에서 {', '.join(labels)} 의심 영역 {len(boxes)}곳을 탐지했습니다. 실제 손상과 정도는 추가 확인이 필요합니다.",
        "care_suggestion": "무리한 사용·마찰과 습기·열을 피하고 공식 AS 센터에 점검을 요청하세요. 임의 세척·염색·접착은 피하세요.",
        "damage_location": {"points": points, "boxes": boxes},
        "result": {"analysis_method": "YOLO_DETECTION", "model_version": digest,
                   "localization_method": "DETECTOR_BOX", "damage_count": len(boxes),
                   "requires_review": True, "is_reference_only": True,
                   "severity_policy": "provisional-v1: tear -> DANGER, other detections -> CAUTION",
                   "notice": "탐지 점수는 손상 심각도나 정확도 보장이 아닙니다. 등급은 임시 점검 우선순위이며 전문가 확인이 필요합니다."},
    }


def analyze_yolo(diagnosis):
    path = Path(os.getenv("AURA_YOLO_WEIGHTS", "models/best.pt")).resolve()
    if not path.is_file():
        raise DiagnosisProviderError("학습 가중치가 없습니다.", code="MODEL_NOT_READY")
    try:
        confidence = float(os.getenv("AURA_YOLO_CONF", "0.35"))
        if not 0 < confidence < 1:
            raise ValueError("invalid threshold")
        with _LOCK:
            model, digest = _load_model(str(path), path.stat().st_mtime_ns)
            diagnosis.image.open("rb")
            try:
                with Image.open(diagnosis.image) as source:
                    frame = source.convert("RGB")
            finally:
                diagnosis.image.close()
            prediction = model.predict(frame, conf=confidence, imgsz=960, max_det=20,
                                       device=os.getenv("AURA_YOLO_DEVICE", "cpu"), verbose=False)[0]
            detections = [(int(c), float(s), box) for c, s, box in zip(
                prediction.boxes.cls.cpu().tolist(), prediction.boxes.conf.cpu().tolist(),
                prediction.boxes.xyxyn.cpu().tolist())]
        return build_result(detections, digest)
    except DiagnosisProviderError:
        raise
    except Exception as exc:
        raise DiagnosisProviderError("탐지 실행 실패", code="MODEL_INFERENCE_FAILED") from exc

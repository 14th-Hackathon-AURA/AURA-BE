"""A single, metadata-free coordinate frame for storage, inference and the UI."""
from io import BytesIO
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError
from django.core.files.base import ContentFile
from rest_framework.exceptions import ValidationError

MAX_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 24_000_000


def normalize_upload(upload):
    if upload.size > MAX_BYTES:
        raise ValidationError("사진은 10MB 이하로 업로드해 주세요.")
    try:
        upload.seek(0)
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(upload) as source:
                if source.format not in {"JPEG", "PNG", "WEBP", "GIF"}:
                    raise ValueError("unsupported format")
                if getattr(source, "n_frames", 1) != 1:
                    raise ValueError("animated image")
                if source.width * source.height > MAX_PIXELS:
                    raise ValueError("too many pixels")
                oriented = ImageOps.exif_transpose(source)
                rgba = oriented.convert("RGBA")
                rgb = Image.new("RGB", rgba.size, "white")
                rgb.paste(rgba, mask=rgba.getchannel("A"))
                rgb.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
                out = BytesIO()
                rgb.save(out, format="JPEG", quality=92)
        return ContentFile(out.getvalue(), name="diagnosis.jpg")
    except (OSError, ValueError, UnidentifiedImageError,
            Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ValidationError("정지 사진(JPEG/PNG/WebP/GIF, 2400만 화소 이하)을 업로드해 주세요.") from exc
    finally:
        upload.seek(0)

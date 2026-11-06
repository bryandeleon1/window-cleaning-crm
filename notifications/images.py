"""Shared safe raster-image validation for private photo uploads."""

from __future__ import annotations

from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

MAX_IMAGE_BYTES = 5 * 1024 * 1024
SAFE_FORMATS = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "GIF": "image/gif",
    "WEBP": "image/webp",
}


MAX_IMAGE_PIXELS = 50_000_000
MAX_IMAGE_FRAMES = 100

_TOO_LARGE = "too_large"
_BAD_TYPE = "bad_type"


def _inspect_image(fileobj) -> tuple[str | None, str | None]:
    """Return (content_type, None) for a safe raster image, else (None, reason).

    Reads header dimensions and frame count only; never decodes pixel data.
    """
    try:
        pos = fileobj.tell()
    except Exception:
        pos = None
    try:
        fileobj.seek(0)
        with Image.open(fileobj) as img:
            fmt = img.format
            width, height = img.size
            frames = getattr(img, "n_frames", 1)
            if width <= 0 or height <= 0:
                return None, _BAD_TYPE
            if width * height > MAX_IMAGE_PIXELS or frames > MAX_IMAGE_FRAMES:
                return None, _TOO_LARGE
            img.verify()
        content_type = SAFE_FORMATS.get(fmt or "")
        return (content_type, None) if content_type else (None, _BAD_TYPE)
    except Image.DecompressionBombError:
        return None, _TOO_LARGE
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError):
        return None, _BAD_TYPE
    finally:
        if pos is not None:
            try:
                fileobj.seek(pos)
            except Exception:
                pass


def sniff_image_content_type(fileobj) -> str | None:
    """Return the verified content type for a safe raster image, else None."""
    return _inspect_image(fileobj)[0]


def validate_safe_image(upload) -> None:
    if upload is None:
        return
    if upload.size > MAX_IMAGE_BYTES:
        raise ValidationError("Photos must be 5 MB or smaller.")
    content_type, reason = _inspect_image(upload)
    if reason == _TOO_LARGE:
        raise ValidationError("This photo is too large.")
    if content_type is None:
        raise ValidationError("Upload a JPEG, PNG, GIF, or WebP image.")
    upload.seek(0)

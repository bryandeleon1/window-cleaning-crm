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


def sniff_image_content_type(fileobj) -> str | None:
    """Return the verified content type for a safe raster image, else None."""
    try:
        pos = fileobj.tell()
    except Exception:
        pos = None
    try:
        fileobj.seek(0)
        with Image.open(fileobj) as img:
            fmt = img.format
            img.verify()
        return SAFE_FORMATS.get(fmt or "")
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError):
        return None
    finally:
        if pos is not None:
            try:
                fileobj.seek(pos)
            except Exception:
                pass


def validate_safe_image(upload) -> None:
    if upload is None:
        return
    if upload.size > MAX_IMAGE_BYTES:
        raise ValidationError("Photos must be 5 MB or smaller.")
    if sniff_image_content_type(upload) is None:
        raise ValidationError("Upload a JPEG, PNG, GIF, or WebP image.")
    upload.seek(0)
